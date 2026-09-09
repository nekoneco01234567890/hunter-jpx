#!/usr/bin/env python3
import os
import struct
import glob
import csv
import math

SRC_DIR="/sdcard/Download"

def u16(b,o):
    return struct.unpack_from("<H",b,o)[0]

def u32(b,o):
    return struct.unpack_from("<I",b,o)[0]

def i16(b,o):
    return struct.unpack_from("<h",b,o)[0]

def i32(b,o):
    return struct.unpack_from("<i",b,o)[0]

def f64(b,o):
    return struct.unpack_from("<d",b,o)[0]

OLE_MAGIC=b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

def ole_streams(path):
    with open(path,"rb") as f:
        data=f.read()

    if data[:8] != OLE_MAGIC:
        raise ValueError("NOT_OLE")

    sector_shift=u16(data,30)
    sector_size=1<<sector_shift

    first_dir=u32(data,48)
    first_mini_fat=u32(data,60)
    num_mini_fat=u32(data,64)
    first_difat=u32(data,68)
    num_difat=u32(data,72)

    def sector(n):
        p=(n+1)*sector_size
        return data[p:p+sector_size]

    difat=[]
    for i in range(109):
        v=u32(data,76+i*4)
        if v != 0xffffffff:
            difat.append(v)

    cur=first_difat
    for _ in range(num_difat):
        if cur in (0xfffffffe,0xffffffff):
            break
        sb=sector(cur)
        count=sector_size//4
        for i in range(count-1):
            v=u32(sb,i*4)
            if v != 0xffffffff:
                difat.append(v)
        cur=u32(sb,(count-1)*4)

    fat=[]
    for secno in difat:
        sb=sector(secno)
        for i in range(sector_size//4):
            fat.append(u32(sb,i*4))

    def chain(start):
        out=[]
        seen=set()
        cur=start
        while cur not in (0xfffffffe,0xffffffff):
            if cur >= len(fat):
                break
            if cur in seen:
                raise ValueError("OLE_CHAIN_LOOP")
            seen.add(cur)
            out.append(cur)
            cur=fat[cur]
        return out

    dbytes=b"".join(sector(x) for x in chain(first_dir))

    entries=[]
    for pos in range(0,len(dbytes),128):
        ent=dbytes[pos:pos+128]
        if len(ent)<128:
            break

        name_len=u16(ent,64)
        if name_len>=2:
            raw=ent[:name_len-2]
            name=raw.decode("utf-16le","replace")
        else:
            name=""

        entries.append({
            "name":name,
            "type":ent[66],
            "start":u32(ent,116),
            "size":struct.unpack_from("<Q",ent,120)[0]
        })

    wb_entry=None
    for e in entries:
        if e["type"]==2 and e["name"].lower() in ("workbook","book"):
            wb_entry=e
            break

    if wb_entry is None:
        raise ValueError("WORKBOOK_NOT_FOUND")

    raw=b"".join(sector(x) for x in chain(wb_entry["start"]))
    return entries,raw[:wb_entry["size"]]

def decode_sst_piece(buf,pos,cch,unicode_flag):
    if unicode_flag:
        n=cch*2
        raw=buf[pos:pos+n]
        return raw.decode("utf-16le","replace"),pos+n
    else:
        raw=buf[pos:pos+cch]
        return raw.decode("latin1","replace"),pos+cch

def parse_records(wb):
    pos=0
    records=[]

    while pos+4<=len(wb):
        rid=u16(wb,pos)
        ln=u16(wb,pos+2)
        end=pos+4+ln

        if end>len(wb):
            break

        payload=wb[pos+4:end]
        records.append((rid,payload,pos))
        pos=end

    return records

def build_sst(records):
    """
    SST record 0x00FC plus CONTINUE 0x003C.
    Reconstructs strings conservatively.
    """
    chunks=[]
    active=False

    for rid,payload,pos in records:
        if rid==0x00fc:
            chunks.append(payload)
            active=True
        elif rid==0x003c and active:
            chunks.append(payload)
        elif active:
            # SST has ended
            active=False

    if not chunks:
        return []

    data=b"".join(chunks)

    if len(data)<8:
        return []

    total=u32(data,0)
    unique=u32(data,4)

    strings=[]
    p=8

    # This handles normal BIFF8 SST strings.
    # Continue boundaries are handled approximately through concatenated
    # stream data; unusual split cases are reported rather than invented.
    for _ in range(unique):
        if p+3>len(data):
            break

        cch=u16(data,p)
        flags=data[p+2]
        p+=3

        is_unicode=bool(flags & 0x01)

        if flags & 0x08:
            if p+4>len(data):
                break
            p+=4

        if is_unicode:
            n=cch*2
        else:
            n=cch

        if p+n>len(data):
            break

        raw=data[p:p+n]
        text=raw.decode("utf-16le" if is_unicode else "latin1","replace")
        p+=n
        strings.append(text)

    return strings

def cell_value(rid,payload,sst):
    if rid==0x00fd: # LABELSST
        if len(payload)<10:
            return None
        row=u16(payload,0)
        col=u16(payload,2)
        xf=u16(payload,4)
        idx=u32(payload,6)
        text=sst[idx] if idx<len(sst) else f"<SST:{idx}>"
        return row,col,text

    if rid==0x0204: # LABEL
        if len(payload)<9:
            return None
        row=u16(payload,0)
        col=u16(payload,2)
        cch=u16(payload,6)
        opt=payload[8]
        p=9
        if opt&1:
            raw=payload[p:p+cch*2]
            text=raw.decode("utf-16le","replace")
        else:
            raw=payload[p:p+cch]
            text=raw.decode("latin1","replace")
        return row,col,text

    if rid==0x0203: # NUMBER
        if len(payload)<14:
            return None
        row=u16(payload,0)
        col=u16(payload,2)
        val=f64(payload,6)
        return row,col,val

    if rid==0x027e: # RK
        if len(payload)<10:
            return None
        row=u16(payload,0)
        col=u16(payload,2)
        rk=u32(payload,6)

        if rk&2:
            v=rk>>2
            if rk&1:
                v=v/100.0
        else:
            signed=struct.unpack("<i",struct.pack("<I",rk&0xfffffffc))[0]
            v=signed/4.0

        return row,col,v

    if rid==0x00bd: # MULRK
        if len(payload)<6:
            return None
        row=u16(payload,0)
        first_col=u16(payload,2)
        last_col=u16(payload,len(payload)-2)

        vals=[]
        p=4
        col=first_col

        while p+6<=len(payload)-2:
            xf=u16(payload,p)
            rk=u32(payload,p+2)

            if rk&2:
                v=rk>>2
                if rk&1:
                    v=v/100.0
            else:
                signed=struct.unpack("<i",struct.pack("<I",rk&0xfffffffc))[0]
                v=signed/4.0

            vals.append((row,col,v))
            col+=1
            p+=6

        return vals

    return None

def main():
    files=sorted(glob.glob(os.path.join(SRC_DIR,"stock_val_1_25*.xls")))

    print("========================================")
    print("JPX XLS BIFF SCHEMA INSPECTION V2")
    print("========================================")
    print("FILES =",len(files))

    if not files:
        print("NO_FILES")
        return

    path=files[0]
    print("TARGET =",os.path.basename(path))
    print("SIZE =",os.path.getsize(path))

    entries,wb=ole_streams(path)

    print("----------------------------------------")
    print("OLE STREAMS")
    for e in entries:
        print(
            e["name"],
            "TYPE=",e["type"],
            "SIZE=",e["size"]
        )

    records=parse_records(wb)

    print("----------------------------------------")
    print("BIFF_RECORD_COUNT =",len(records))

    counts={}
    for rid,payload,pos in records:
        counts[rid]=counts.get(rid,0)+1

    names={
        0x0809:"BOF",
        0x000a:"EOF",
        0x00fc:"SST",
        0x003c:"CONTINUE",
        0x00fd:"LABELSST",
        0x0204:"LABEL",
        0x0203:"NUMBER",
        0x027e:"RK",
        0x00bd:"MULRK",
        0x0201:"BLANK",
        0x00e0:"XF",
        0x0200:"DIMENSIONS",
    }

    print("RECORD_TYPES")
    for rid,count in sorted(counts.items(),key=lambda x:(-x[1],x[0])):
        print(hex(rid),names.get(rid,"UNKNOWN"),count)

    sst=build_sst(records)

    print("----------------------------------------")
    print("SST_STRINGS =",len(sst))

    if sst:
        print("SST_SAMPLE")
        for i,s in enumerate(sst[:80]):
            print(f"{i}: {s!r}")

    print("----------------------------------------")
    print("CELL_SAMPLE")

    shown=0
    for rid,payload,pos in records:
        v=cell_value(rid,payload,sst)

        if rid==0x00bd and isinstance(v,list):
            for x in v:
                print(
                    "ROW=",x[0]+1,
                    "COL=",x[1]+1,
                    "VALUE=",repr(x[2])
                )
                shown+=1
                if shown>=80:
                    break
        elif v is not None:
            row,col,value=v
            print(
                "ROW=",row+1,
                "COL=",col+1,
                "VALUE=",repr(value)
            )
            shown+=1

        if shown>=80:
            break

    print("----------------------------------------")
    print("INSPECTION_COMPLETE")

if __name__=="__main__":
    main()
