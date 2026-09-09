#!/usr/bin/env python3
import os
import struct
import glob
import math

SRC_DIR="/sdcard/Download"
OLE_MAGIC=b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

def u16(b,o):
    return struct.unpack_from("<H",b,o)[0]

def u32(b,o):
    return struct.unpack_from("<I",b,o)[0]

def u64(b,o):
    return struct.unpack_from("<Q",b,o)[0]

def f64(b,o):
    return struct.unpack_from("<d",b,o)[0]

def ole_stream(path):
    with open(path,"rb") as f:
        data=f.read()

    if data[:8] != OLE_MAGIC:
        raise ValueError("NOT_OLE")

    sector_size=1 << u16(data,30)
    first_dir=u32(data,48)
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
        n=sector_size//4
        for i in range(n-1):
            v=u32(sb,i*4)
            if v != 0xffffffff:
                difat.append(v)
        cur=u32(sb,(n-1)*4)

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
            if cur>=len(fat) or cur in seen:
                break
            seen.add(cur)
            out.append(cur)
            cur=fat[cur]
        return out

    directory=b"".join(sector(x) for x in chain(first_dir))

    workbook=None

    for p in range(0,len(directory),128):
        e=directory[p:p+128]
        if len(e)<128:
            continue

        name_len=u16(e,64)
        if name_len>=2:
            name=e[:name_len-2].decode("utf-16le","replace")
        else:
            name=""

        typ=e[66]
        start=u32(e,116)
        size=u64(e,120)

        if typ==2 and name.lower() in ("workbook","book"):
            workbook=(start,size,name)

    if workbook is None:
        raise ValueError("WORKBOOK_NOT_FOUND")

    start,size,name=workbook
    raw=b"".join(sector(x) for x in chain(start))
    return raw[:size]

def records(wb):
    out=[]
    p=0

    while p+4<=len(wb):
        rid=u16(wb,p)
        ln=u16(wb,p+2)
        end=p+4+ln

        if end>len(wb):
            break

        out.append((rid,wb[p+4:end],p))
        p=end

    return out

def parse_sst(records_list):
    """
    BIFF8 SST parser with CONTINUE-aware reconstruction.

    Important:
    CONTINUE payload begins with a compression flag when continuing
    a Unicode string. We therefore cannot simply concatenate SST+CONTINUE.
    """

    blocks=[]
    in_sst=False

    for rid,payload,pos in records_list:
        if rid==0x00fc:
            blocks.append(payload)
            in_sst=True
        elif rid==0x003c and in_sst:
            blocks.append(payload)
        elif in_sst:
            break

    if not blocks:
        return [],"NO_SST"

    first=blocks[0]

    if len(first)<8:
        return [],"SST_TOO_SHORT"

    total=u32(first,0)
    unique=u32(first,4)

    # Create a cursor over SST + CONTINUE records while preserving boundaries.
    segments=blocks

    seg=0
    pos=8

    strings=[]

    def get_bytes(n, unicode_mode):
        nonlocal seg,pos

        out=bytearray()

        while n>0:
            if seg>=len(segments):
                raise ValueError("SST_EOF")

            cur=segments[seg]

            if pos>=len(cur):
                seg+=1
                pos=0

                # For a continuation of a Unicode string, BIFF8 inserts
                # one option byte before the continuation text.
                if seg<len(segments) and unicode_mode:
                    flag=segments[seg][0]
                    pos=1
                    unicode_mode=(flag & 0x01)!=0

                continue

            take=min(n,len(cur)-pos)
            out.extend(cur[pos:pos+take])
            pos+=take
            n-=take

        return bytes(out)

    try:
        for idx in range(unique):
            # cch + option flags
            if seg>=len(segments):
                raise ValueError("SST_NO_CCH")

            # Ensure enough bytes for header
            while pos+3>len(segments[seg]):
                seg+=1
                pos=0

            cch=u16(segments[seg],pos)
            flags=segments[seg][pos+2]
            pos+=3

            is_unicode=bool(flags & 0x01)

            # Rich string formatting runs
            rich_count=0
            if flags & 0x08:
                if pos+2>len(segments[seg]):
                    # Extremely unusual boundary case
                    raw=get_bytes(2,False)
                    rich_count=u16(raw,0)
                else:
                    rich_count=u16(segments[seg],pos)
                    pos+=2

            # Far-East phonetic data
            phonetic_size=0
            if flags & 0x04:
                if pos+4>len(segments[seg]):
                    raw=get_bytes(4,False)
                    phonetic_size=u32(raw,0)
                else:
                    phonetic_size=u32(segments[seg],pos)
                    pos+=4

            # Character data
            chars=[]

            while len(chars)<cch:
                if seg>=len(segments):
                    raise ValueError("SST_STRING_EOF")

                cur=segments[seg]

                if pos>=len(cur):
                    seg+=1
                    pos=0

                    if seg<len(segments):
                        # CONTINUE starts with encoding flag
                        flag=segments[seg][0]
                        pos=1
                        is_unicode=bool(flag & 0x01)
                    continue

                remain_chars=cch-len(chars)

                if is_unicode:
                    avail=(len(cur)-pos)//2
                    take=min(remain_chars,avail)
                    raw=cur[pos:pos+take*2]
                    chars.append(raw.decode("utf-16le","replace"))
                    pos+=take*2
                else:
                    take=min(remain_chars,len(cur)-pos)
                    raw=cur[pos:pos+take]
                    chars.append(raw.decode("latin1","replace"))
                    pos+=take

            # Skip rich formatting runs
            if rich_count:
                need=rich_count*4
                while need:
                    if seg>=len(segments):
                        raise ValueError("SST_RICH_EOF")
                    take=min(need,len(segments[seg])-pos)
                    pos+=take
                    need-=take
                    if need and pos>=len(segments[seg]):
                        seg+=1
                        pos=0

            # Skip phonetic/ext data
            if phonetic_size:
                need=phonetic_size
                while need:
                    if seg>=len(segments):
                        raise ValueError("SST_PHONETIC_EOF")
                    take=min(need,len(segments[seg])-pos)
                    pos+=take
                    need-=take
                    if need and pos>=len(segments[seg]):
                        seg+=1
                        pos=0

            strings.append("".join(chars))

    except Exception as e:
        return strings,"PARTIAL:"+type(e).__name__+":"+str(e)

    status="PASS" if len(strings)==unique else "COUNT_MISMATCH"
    return strings,status

def cell_labelsst(payload,sst):
    if len(payload)<10:
        return None
    row=u16(payload,0)
    col=u16(payload,2)
    idx=u32(payload,6)
    text=sst[idx] if idx<len(sst) else f"<SST:{idx}>"
    return row,col,text

def cell_number(payload):
    if len(payload)<14:
        return None
    return u16(payload,0),u16(payload,2),f64(payload,6)

def cell_rk(payload):
    if len(payload)<10:
        return None

    row=u16(payload,0)
    col=u16(payload,2)
    rk=u32(payload,6)

    if rk&2:
        value=rk>>2
        if rk&1:
            value=value/100.0
    else:
        signed=struct.unpack("<i",struct.pack("<I",rk&0xfffffffc))[0]
        value=signed/4.0

    return row,col,value

def main():
    files=sorted(glob.glob(os.path.join(SRC_DIR,"stock_val_1_25*.xls")))

    print("========================================")
    print("JPX XLS BIFF SCHEMA INSPECTION V3")
    print("========================================")
    print("FILES_FOUND =",len(files))

    if not files:
        return

    path=files[0]
    print("TARGET =",os.path.basename(path))
    print("SIZE =",os.path.getsize(path))

    wb=ole_stream(path)
    recs=records(wb)

    counts={}
    for rid,payload,pos in recs:
        counts[rid]=counts.get(rid,0)+1

    names={
        0x0809:"BOF",
        0x000a:"EOF",
        0x00fc:"SST",
        0x003c:"CONTINUE",
        0x00fd:"LABELSST",
        0x0203:"NUMBER",
        0x027e:"RK",
        0x00bd:"MULRK",
        0x00e0:"XF",
        0x0200:"DIMENSIONS",
    }

    print("----------------------------------------")
    print("BIFF_RECORDS =",len(recs))
    print("RECORD_TYPES")

    for rid,n in sorted(counts.items(),key=lambda x:(-x[1],x[0])):
        print(hex(rid),names.get(rid,"UNKNOWN"),n)

    sst,status=parse_sst(recs)

    print("----------------------------------------")
    print("SST_STATUS =",status)
    print("SST_EXPECTED_UNIQUE =",u32(next(p for r,p,_ in recs if r==0x00fc),4))
    print("SST_PARSED =",len(sst))

    print("----------------------------------------")
    print("SST_SAMPLE")

    for i,s in enumerate(sst[:120]):
        print(f"{i}: {s!r}")

    print("----------------------------------------")
    print("LABELSST_SAMPLE")

    shown=0

    for rid,payload,pos in recs:
        if rid==0x00fd:
            x=cell_labelsst(payload,sst)
            if x:
                print(
                    "ROW=",x[0]+1,
                    "COL=",x[1]+1,
                    "VALUE=",repr(x[2])
                )
                shown+=1

        if shown>=120:
            break

    print("----------------------------------------")
    print("NUMBER_SAMPLE")

    shown=0

    for rid,payload,pos in recs:
        if rid==0x0203:
            x=cell_number(payload)
            if x:
                print(
                    "ROW=",x[0]+1,
                    "COL=",x[1]+1,
                    "VALUE=",repr(x[2])
                )
                shown+=1

        elif rid==0x027e:
            x=cell_rk(payload)
            if x:
                print(
                    "ROW=",x[0]+1,
                    "COL=",x[1]+1,
                    "VALUE=",repr(x[2])
                )
                shown+=1

        if shown>=120:
            break

    print("----------------------------------------")
    print("V3_INSPECTION_COMPLETE")

if __name__=="__main__":
    main()
