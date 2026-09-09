import os
import re
import csv
import struct
from glob import glob
from collections import Counter

SRC_DIR = "/sdcard/Download"
OUT_DIR = "data/jpx_weekly_investor"

os.makedirs(OUT_DIR, exist_ok=True)

RAW_OUT = os.path.join(OUT_DIR, "jpx_weekly_investor_flow_raw.csv")
AUDIT_OUT = os.path.join(OUT_DIR, "jpx_weekly_investor_flow_audit.csv")
SUMMARY_OUT = os.path.join(OUT_DIR, "jpx_weekly_investor_flow_summary.csv")

SEC = 512


def u16(b,p):
    return struct.unpack_from("<H",b,p)[0]

def u32(b,p):
    return struct.unpack_from("<I",b,p)[0]


def ole_stream(path):
    with open(path,"rb") as f:
        data=f.read()

    if data[:8] != bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1"):
        raise ValueError("NOT_OLE")

    sec_size=1<<u16(data,30)
    first_dir=u32(data,48)

    difat=[]
    for i in range(109):
        x=u32(data,76+i*4)
        if x != 0xffffffff:
            difat.append(x)

    first_difat=u32(data,68)
    num_difat=u32(data,72)

    cur=first_difat

    for _ in range(num_difat):
        if cur in (0xfffffffe,0xffffffff):
            break

        off=512+cur*sec_size

        for j in range(sec_size//4-1):
            x=u32(data,off+j*4)
            if x != 0xffffffff:
                difat.append(x)

        cur=u32(data,off+(sec_size//4-1)*4)

    fat=[]

    for s in difat:
        off=512+s*sec_size
        for j in range(sec_size//4):
            fat.append(u32(data,off+j*4))

    def chain(start):
        out=[]
        seen=set()
        s=start

        while s not in (0xfffffffe,0xffffffff) and s<len(fat):
            if s in seen:
                raise ValueError("OLE_CHAIN_LOOP")

            seen.add(s)
            out.append(s)
            s=fat[s]

        return out

    directory=bytearray()

    for s in chain(first_dir):
        off=512+s*sec_size
        directory += data[off:off+sec_size]

    target=None

    for p in range(0,len(directory),128):
        if p+128>len(directory):
            break

        name_len=u16(directory,p+64)

        if name_len>=2:
            name=directory[p:p+name_len-2].decode(
                "utf-16le",
                errors="replace"
            )
        else:
            name=""

        obj_type=directory[p+66]

        if obj_type==2 and name=="Workbook":
            target=(
                u32(directory,p+116),
                u32(directory,p+120)
            )
            break

    if target is None:
        raise ValueError("WORKBOOK_NOT_FOUND")

    start,size=target
    out=bytearray()

    for s in chain(start):
        off=512+s*sec_size
        out += data[off:off+sec_size]

        if len(out)>=size:
            break

    return bytes(out[:size])


def records(wb):
    p=0

    while p+4<=len(wb):
        rid=u16(wb,p)
        ln=u16(wb,p+2)

        if p+4+ln>len(wb):
            break

        yield rid,wb[p+4:p+4+ln],p
        p += 4+ln


def parse_sst(wb):
    recs=list(records(wb))

    for i,(rid,payload,pos) in enumerate(recs):

        if rid != 0x00fc:
            continue

        total=u32(payload,0)
        unique=u32(payload,4)

        segments=[payload[8:]]

        j=i+1

        while j<len(recs) and recs[j][0]==0x003c:
            segments.append(recs[j][1])
            j+=1

        data=b"".join(segments)
        p=0
        strings=[]

        def read(n):
            nonlocal p
            if p+n>len(data):
                raise ValueError("SST_STRING_EOF")
            x=data[p:p+n]
            p+=n
            return x

        def r8():
            return read(1)[0]

        def r16():
            return struct.unpack("<H",read(2))[0]

        def r32():
            return struct.unpack("<I",read(4))[0]

        for _ in range(unique):

            cch=r16()
            option=r8()

            is_unicode=bool(option&1)
            has_rich=bool(option&8)
            has_phonetic=bool(option&4)

            rich_count=r16() if has_rich else 0
            phonetic_size=r32() if has_phonetic else 0

            if rich_count:
                read(rich_count*4)

            if is_unicode:
                s=read(cch*2).decode(
                    "utf-16le",
                    errors="replace"
                )
            else:
                s=read(cch).decode(
                    "latin1",
                    errors="replace"
                )

            if phonetic_size:
                read(phonetic_size)

            strings.append(s)

        if len(strings)!=unique:
            raise ValueError("SST_COUNT_MISMATCH")

        return total,unique,strings

    raise ValueError("SST_NOT_FOUND")


def clean(v):
    if v is None:
        return ""

    v=str(v).replace("\r"," ").replace("\n"," ")
    return re.sub(r"\s+"," ",v).strip()


def num(v):
    v=clean(v)

    if not v:
        return None

    # negative values may appear as "-65,723,365"
    try:
        return float(v.replace(",",""))
    except:
        return None


def detect_date(filename):
    m=re.search(r"stock_val_1_(\d{6})\.xls$",filename)

    if not m:
        return ""

    s=m.group(1)

    # YYMMDD
    yy=int(s[:2])
    mm=int(s[2:4])
    dd=int(s[4:6])

    return f"20{yy:02d}-{mm:02d}-{dd:02d}"


def get_cells(wb,sst):

    cells={}

    for rid,payload,pos in records(wb):

        if rid==0x00fd and len(payload)>=10:

            row=u16(payload,0)
            col=u16(payload,2)
            idx=u32(payload,6)

            value=sst[idx] if idx<len(sst) else ""

            cells[(row,col)]=clean(value)

    return cells


def row(cells,r):

    return {
        c:cells.get((r,c),"")
        for c in range(12)
    }


def make_record(date,source,section,category,side,amount,ratio,net):

    return {
        "DATE":date,
        "SOURCE_FILE":os.path.basename(source),
        "SECTION":section,
        "CATEGORY":category,
        "SIDE":side,
        "AMOUNT":amount,
        "RATIO":ratio,
        "NET":net
    }


def extract_file(path):

    wb=ole_stream(path)

    total,unique,sst=parse_sst(wb)

    if unique!=len(sst):
        raise ValueError("SST_COUNT_MISMATCH")

    cells=get_cells(wb,sst)

    date=detect_date(path)

    rows=[]

    # Main investor categories.
    # Rows 13 onward contain the main "委託計" section.
    #
    # We intentionally identify categories by their Japanese labels
    # instead of assuming fixed row numbers across every workbook.

    category_alias={
        "個人":"Individuals",
        "海外投資家":"Foreigners",
        "証券会社":"Securities Cos.",
        "投資信託":"Investment Trusts",
        "事業法人":"Business Cos.",
        "その他法人等":"Other Corporations",
        "生保・損保":"Life & Non-Life Insurance",
        "都銀・地銀等":"Banks",
        "信用金庫・信用組合":"Credit Unions",
    }

    # Scan rows and identify Japanese category labels.
    # Side rows immediately below category rows contain Sales/Purchases.
    max_row=max((r for r,c in cells),default=0)

    current_category=""

    for r in range(1,max_row+1):

        label=cells.get((r,0),"")
        label1=cells.get((r,1),"")
        label2=cells.get((r,2),"")
        label3=cells.get((r,3),"")
        label4=cells.get((r,4),"")
        label5=cells.get((r,5),"")
        label6=cells.get((r,6),"")
        label8=cells.get((r,8),"")
        label9=cells.get((r,9),"")
        label10=cells.get((r,10),"")

        # category detection
        if label in category_alias:
            current_category=label

        # Main sales / purchases rows
        if label1 in ("売り","買い") and label2 in ("Sales","Purchases"):

            side=label1

            amount1=label4
            ratio1=label5
            net1=label6

            amount2=label8
            ratio2=label9
            net2=label10

            # First numeric pair = current reporting period
            # Second numeric pair = cumulative period in the source table.
            #
            # Keep both as separate records.
            a1=num(amount1)
            q1=num(ratio1)
            n1=num(net1)

            a2=num(amount2)
            q2=num(ratio2)
            n2=num(net2)

            if current_category:

                rows.append(make_record(
                    date,path,
                    "委託内訳",
                    current_category,
                    side,
                    a1,q1,n1
                ))

                rows.append(make_record(
                    date,path,
                    "委託内訳累計",
                    current_category,
                    side,
                    a2,q2,n2
                ))

    # Dedicated individual cash/margin and proprietary cash/margin.
    special_map={
        "個人現金":"Individual Cash",
        "個人信用":"Individual Margin",
        "自己現金":"Proprietary Cash",
        "自己信用":"Proprietary Margin",
    }

    for r in range(1,max_row+1):

        label=cells.get((r,0),"")

        if label not in special_map:
            continue

        rows.append(make_record(
            date,path,
            "個人/自己区分",
            special_map[label],
            "TOTAL",
            num(cells.get((r,2),"")),
            num(cells.get((r,3),"")),
            None
        ))

        # columns 4/5 are the second side/period
        rows.append(make_record(
            date,path,
            "個人/自己区分累計",
            special_map[label],
            "TOTAL",
            num(cells.get((r,4),"")),
            num(cells.get((r,5),"")),
            None
        ))

    # Foreign institutions / individuals
    # Rows under the dedicated foreign section.
    foreign_rows=False

    for r in range(1,max_row+1):

        label=cells.get((r,0),"")
        l1=cells.get((r,1),"")
        l2=cells.get((r,2),"")

        if "海外投資家売買における" in label:
            foreign_rows=True
            continue

        if foreign_rows and label in ("法人","個人"):

            rows.append(make_record(
                date,path,
                "海外投資家内訳",
                "Foreign " + label,
                "売り",
                num(cells.get((r,3),"")),
                None,
                None
            ))

            rows.append(make_record(
                date,path,
                "海外投資家内訳",
                "Foreign " + label,
                "買い",
                num(cells.get((r,5),"")),
                None,
                None
            ))

    return {
        "source":path,
        "date":date,
        "total":total,
        "unique":unique,
        "sst":len(sst),
        "cells":len(cells),
        "rows":rows
    }


def main():

    files=sorted(glob(
        os.path.join(SRC_DIR,"stock_val_1_*.xls")
    ))

    print("========================================")
    print("JPX WEEKLY INVESTOR FLOW BUILDER")
    print("========================================")
    print("FILES =",len(files))

    raw_fields=[
        "DATE",
        "SOURCE_FILE",
        "SECTION",
        "CATEGORY",
        "SIDE",
        "AMOUNT",
        "RATIO",
        "NET"
    ]

    audit_fields=[
        "SOURCE_FILE",
        "DATE",
        "SST_TOTAL",
        "SST_UNIQUE",
        "SST_PARSED",
        "CELL_COUNT",
        "EXTRACTED_ROWS",
        "STATUS",
        "ERROR"
    ]

    counts=Counter()

    with open(RAW_OUT,"w",newline="",encoding="utf-8-sig") as rf, \
         open(AUDIT_OUT,"w",newline="",encoding="utf-8-sig") as af:

        rw=csv.DictWriter(rf,fieldnames=raw_fields)
        aw=csv.DictWriter(af,fieldnames=audit_fields)

        rw.writeheader()
        aw.writeheader()

        for i,path in enumerate(files,1):

            name=os.path.basename(path)

            try:

                result=extract_file(path)

                for rec in result["rows"]:
                    rw.writerow(rec)

                aw.writerow({
                    "SOURCE_FILE":name,
                    "DATE":result["date"],
                    "SST_TOTAL":result["total"],
                    "SST_UNIQUE":result["unique"],
                    "SST_PARSED":result["sst"],
                    "CELL_COUNT":result["cells"],
                    "EXTRACTED_ROWS":len(result["rows"]),
                    "STATUS":"PASS",
                    "ERROR":""
                })

                counts["PASS"]+=1

                print(
                    f"[{i:02d}/{len(files):02d}] "
                    f"PASS {name} "
                    f"rows={len(result['rows'])}"
                )

            except Exception as e:

                aw.writerow({
                    "SOURCE_FILE":name,
                    "DATE":detect_date(path),
                    "SST_TOTAL":"",
                    "SST_UNIQUE":"",
                    "SST_PARSED":"",
                    "CELL_COUNT":"",
                    "EXTRACTED_ROWS":0,
                    "STATUS":"FAIL",
                    "ERROR":type(e).__name__+":"+str(e)
                })

                counts["FAIL"]+=1

                print(
                    f"[{i:02d}/{len(files):02d}] "
                    f"FAIL {name} "
                    f"{type(e).__name__}:{e}"
                )

    # Summary
    total=len(files)
    passed=counts["PASS"]
    failed=counts["FAIL"]

    with open(SUMMARY_OUT,"w",newline="",encoding="utf-8-sig") as f:

        w=csv.writer(f)
        w.writerow(["METRIC","VALUE"])

        w.writerow(["SOURCE_FILES",total])
        w.writerow(["PASS_FILES",passed])
        w.writerow(["FAIL_FILES",failed])

        w.writerow([
            "FILE_AUDIT_STATUS",
            "PASS" if total==52 and failed==0 else "PARTIAL"
        ])

        w.writerow([
            "RAW_OUTPUT",
            RAW_OUT
        ])

        w.writerow([
            "AUDIT_OUTPUT",
            AUDIT_OUT
        ])

    print()
    print("========================================")
    print("FINAL")
    print("========================================")
    print("SOURCE_FILES =",total)
    print("PASS_FILES   =",passed)
    print("FAIL_FILES   =",failed)

    if total==52 and failed==0:
        print("WEEKLY_INVESTOR_FLOW_AUDIT = PASS")
    else:
        print("WEEKLY_INVESTOR_FLOW_AUDIT = PARTIAL")

    print()
    print("RAW   =",RAW_OUT)
    print("AUDIT =",AUDIT_OUT)
    print("SUMMARY =",SUMMARY_OUT)


if __name__=="__main__":
    main()
