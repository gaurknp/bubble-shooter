# BOQ Live Rate Calculator (Excel + Zoho Sheet) — Complete Build File

This file is a **ready-to-implement blueprint** for your workbook with smart search, auto-match, rate comparison, manual override options, and a separate finalized output sheet.

---

## 1) Workbook Structure (Sheets)

Create the sheets in this exact order:

1. `SEARCH`
2. `LIVE_RATE_CALCULATOR`
3. `BOQ_MASTER_ITEMS`
4. `PRICING_SCENARIOS`
5. `BOQ_PASTE_BY_DESCRIPTION`
6. `PROJECT_BOQ` *(final selected lines only)*
7. `LISTS` *(helper lists + validation)*

---

## 2) Core Data Tables

## `BOQ_MASTER_ITEMS` columns

| Col | Header |
|---|---|
| A | Item Code |
| B | Category |
| C | Sub-Category |
| D | Item Description |
| E | Specification |
| F | Unit |
| G | Base Cost Rate |
| H | Cost Last Updated |
| I | Vendor Reference |
| J | Remarks |

> Convert range to Excel table named `tblItems` (Zoho: keep same headers in row 1).

## `PRICING_SCENARIOS` columns

| Col | Header |
|---|---|
| A | Scenario Code |
| B | Scenario Name |
| C | Job Risk Location % |
| D | Airport Overhead % |
| E | Outstation Overhead % |
| F | Logistics Factor % |
| G | Union/Matadi Cost % |
| H | Far-off Location % |
| I | Missing Amenities Water/Elect % |
| J | High Height % |
| K | Valid From |
| L | Valid Till |
| M | Approved By |

> Convert range to table `tblScenarios`.

---

## 3) SEARCH Sheet (fast keyword search)

### Input
- `B3` = search keyword.

### Headers row (A6:H6)
`Item Code | Category | Sub-Category | Item Description | Unit | Base Cost Rate | Last Updated | Remarks`

### Excel 365 formula (dynamic spill) in `A7`
```excel
=LET(
 q,LOWER(TRIM($B$3)),
 data,tblItems,
 IF(q="",
   "",
   FILTER(
     CHOOSE({1,2,3,4,5,6,7,8},data[Item Code],data[Category],data[Sub-Category],data[Item Description],data[Unit],data[Base Cost Rate],data[Cost Last Updated],data[Remarks]),
     ISNUMBER(SEARCH(q,LOWER(data[Item Description]&" "&data[Item Code]&" "&data[Category]&" "&data[Sub-Category]))),
     "No match"
   )
 )
)
```

### Zoho-compatible approach (row-by-row)
In `A7` (copy right to H and down):
```excel
=IFERROR(INDEX(BOQ_MASTER_ITEMS!$A:$J,SMALL(IF(ISNUMBER(SEARCH(LOWER($B$3),LOWER(BOQ_MASTER_ITEMS!$A$2:$A$9999&" "&BOQ_MASTER_ITEMS!$D$2:$D$9999&" "&BOQ_MASTER_ITEMS!$B$2:$B$9999&" "&BOQ_MASTER_ITEMS!$C$2:$C$9999))),ROW(BOQ_MASTER_ITEMS!$A$2:$A$9999)),ROW(A1)),COLUMN(A1)),"")
```
*(Array behavior may require Zoho compatible array entry depending tenant settings.)*

---

## 4) LIVE_RATE_CALCULATOR Sheet (single-item instant pricing)

## Inputs
- `B3` Customer
- `B4` Project
- `B5` Scenario Code
- `B6` Item Code *(manual selection OR auto from search if single match)*
- `E4` Search text

## Match helpers

### Auto item code (only if exactly one match) in `E5`
```excel
=LET(
 q,LOWER(TRIM($E$4)),
 codes,FILTER(tblItems[Item Code],ISNUMBER(SEARCH(q,LOWER(tblItems[Item Description]&" "&tblItems[Item Code]))),""),
 IF(COUNTA(codes)=1,INDEX(codes,1),"MULTIPLE/NO MATCH")
)
```

### Match list (Item Code | Description) in `E7`
```excel
=LET(
 q,LOWER(TRIM($E$4)),
 FILTER(tblItems[Item Code]&" | "&tblItems[Item Description],ISNUMBER(SEARCH(q,LOWER(tblItems[Item Description]&" "&tblItems[Item Code]))),"No matches")
)
```

## Item fetch formulas
- `B8` Description
```excel
=IFERROR(XLOOKUP($B$6,tblItems[Item Code],tblItems[Item Description],""),"")
```
- `B9` Unit
```excel
=IFERROR(XLOOKUP($B$6,tblItems[Item Code],tblItems[Unit],""),"")
```
- `B10` Base Cost
```excel
=IFERROR(XLOOKUP($B$6,tblItems[Item Code],tblItems[Base Cost Rate],0),0)
```

## Scenario factors (B11:B18)
Use XLOOKUP against `tblScenarios[Scenario Code]` for each percentage column.

Example for `B11` (Job Risk %):
```excel
=IFERROR(XLOOKUP($B$5,tblScenarios[Scenario Code],tblScenarios[Job Risk Location %],0),0)
```

## Total scenario uplift in `B19`
```excel
=SUM(B11:B18)
```

## Scenario Rate in `B20`
```excel
=B10*(1+B19)
```

## Override % in `B21` (manual)

## Final Rate in `B22`
```excel
=B20*(1+B21)
```

---

## 5) BOQ_PASTE_BY_DESCRIPTION (bulk processing + multi-match compare)

Use row 8 as first data row.

| Col | Header | Logic |
|---|---|---|
| A | Customer | manual/dropdown |
| B | Project | manual/dropdown |
| C | Scenario | dropdown from `tblScenarios[Scenario Code]` |
| D | Pasted Item Description | pasted text |
| E | Pasted Unit (optional) | manual |
| F | Qty | numeric |
| G | Matched Item Code | best pick / manual final |
| H | Match Count | automatic |
| I | Status | OK / NOT FOUND / MULTIPLE-REVIEW |
| J | Matched Master Description | from selected code |
| K | Unit (Master) | from selected code |
| L | Base Cost | from selected code |
| M | Scenario Rate | base × scenario factors |
| N | Override Rate | manual |
| O | Final Rate | M + override |
| P | Amount | Qty × Final Rate |
| Q:U | Suggestion 1..5 | top five probable matches |
| V | Pick Suggestion # | user chooses 1..5 |
| W | Selected? | FINAL / HOLD |

### Match Count `H8`
```excel
=IF(D8="",0,SUMPRODUCT(--ISNUMBER(SEARCH(LOWER(D8),LOWER(tblItems[Item Description])))) )
```

### Status `I8`
```excel
=IF(D8="","",IF(H8=0,"NOT FOUND",IF(H8=1,"OK","MULTIPLE-REVIEW")))
```

### Suggestions using score (creative + efficient)
Build a helper score in `LISTS` sheet using weighted keywords (or use Office 365 formula directly).

Office 365 direct for Suggestion 1 (`Q8`):
```excel
=LET(
 q,LOWER($D8),
 desc,tblItems[Item Description],
 code,tblItems[Item Code],
 score,(--ISNUMBER(SEARCH(q,LOWER(desc))))*100 + (LEN(q)-LEN(SUBSTITUTE(LOWER(desc),q,""))),
 ranked,SORTBY(HSTACK(code,desc,score),score,-1),
 IFERROR(INDEX(ranked,1,1)&" | "&INDEX(ranked,1,2),"")
)
```

For Suggestion 2..5 use row index 2..5 in the same `INDEX(ranked,n,...)` pattern.

### Picked code from suggestion number `G8`
```excel
=IFERROR(
 IF(V8="",LEFT(Q8,FIND(" |",Q8)-1),
    LEFT(CHOOSE(V8,Q8,R8,S8,T8,U8),FIND(" |",CHOOSE(V8,Q8,R8,S8,T8,U8))-1)
 ),
 ""
)
```

### Description/Unit/Base
- `J8`
```excel
=IFERROR(XLOOKUP($G8,tblItems[Item Code],tblItems[Item Description],""),"")
```
- `K8`
```excel
=IFERROR(XLOOKUP($G8,tblItems[Item Code],tblItems[Unit],""),"")
```
- `L8`
```excel
=IFERROR(XLOOKUP($G8,tblItems[Item Code],tblItems[Base Cost Rate],0),0)
```

### Scenario total factor helper (can be hidden `LISTS!B:B`)
Scenario factor for row uses lookup from `C8`.

### Scenario Rate `M8`
```excel
=L8*(1+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Job Risk Location %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Airport Overhead %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Outstation Overhead %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Logistics Factor %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Union/Matadi Cost %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Far-off Location %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[Missing Amenities Water/Elect %],0),0)+
 IFERROR(XLOOKUP($C8,tblScenarios[Scenario Code],tblScenarios[High Height %],0),0)
)
```

### Final Rate + Amount
- `O8`
```excel
=M8*(1+IF(N8="",0,N8))
```
- `P8`
```excel
=IFERROR(F8*O8,0)
```

Copy formulas down as far as needed.

---

## 6) PROJECT_BOQ (separate finalized sheet)

Show only rows marked `FINAL` from bulk sheet.

### Excel 365 in `A2`
```excel
=FILTER(BOQ_PASTE_BY_DESCRIPTION!A:W,BOQ_PASTE_BY_DESCRIPTION!W:W="FINAL","No finalized lines")
```

### Zoho fallback
Use a sheet filter on column `W = FINAL`, then copy visible rows (or use Query Table if available in your Zoho tier).

---

## 7) Data Validation / UX Enhancements

1. Scenario dropdown in `LIVE_RATE_CALCULATOR!B5` and `BOQ_PASTE_BY_DESCRIPTION!C:C` from `PRICING_SCENARIOS!A2:A`.
2. `V: Pick Suggestion #` validation list = `1,2,3,4,5`.
3. Conditional formatting:
   - `NOT FOUND` = red.
   - `MULTIPLE-REVIEW` = amber.
   - `OK` = green.
4. Protect formula columns and leave input columns editable only.

---

## 8) Zoho Sheet Compatibility Notes

- Prefer `INDEX + MATCH + IFERROR + SEARCH + SUMPRODUCT` if `FILTER/LET/XLOOKUP` are unavailable.
- Keep helper columns in `LISTS` to avoid heavy array formulas in every row.
- Use finite ranges (`$2:$5000`) instead of whole-column references for speed.
- Avoid volatile formulas where possible.

---

## 9) Recommended “Latest Formula” Pattern

When available (Excel 365), use this stack for best performance and maintainability:
- `LET()` to avoid repeated expressions.
- `FILTER()` for search results.
- `XLOOKUP()` for key-based reads.
- `SORTBY()` + score logic for ranked suggestions.
- `HSTACK()` for compact multi-column dynamic arrays.

This gives your team a workflow:
1. Search BOQ item quickly.
2. Compare multiple possible rates automatically.
3. Pick best suggestion.
4. Finalize rows.
5. Auto-publish a clean selected BOQ in `PROJECT_BOQ`.

