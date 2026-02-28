# Accounting Automation Formula Template (Excel + Zoho Sheet)

This template gives you an invoice tracker with automatic due-date reminders and report formulas for monthly, quarterly, unpaid, due, and overdue summaries.

## 1) Base Sheet: `Invoices`

Create a sheet named **Invoices** with these columns:

| Col | Header |
|---|---|
| A | Invoice_ID |
| B | Customer |
| C | Invoice_Date |
| D | Due_Date |
| E | Amount |
| F | Paid_Amount |
| G | Status |
| H | Balance |
| I | Days_To_Due |
| J | Reminder |
| K | Month_Key |
| L | Quarter_Key |

### 1.1 Data entry rules
- `Invoice_Date` and `Due_Date` should be date format.
- `Amount` and `Paid_Amount` should be currency/number.
- `Status` can be entered manually (`Paid`, `Unpaid`, `Partially Paid`) or automated using formula.

## 2) Row formulas (Excel)

Assume first data row is row 2:

- **G2 (Auto Status)**
```excel
=IF(F2>=E2,"Paid",IF(F2=0,"Unpaid","Partially Paid"))
```

- **H2 (Balance)**
```excel
=MAX(E2-F2,0)
```

- **I2 (Days_To_Due)**
```excel
=D2-TODAY()
```

- **J2 (Reminder)**
```excel
=IF(H2=0,"Closed",IF(D2<TODAY(),"Overdue",IF(D2=TODAY(),"Due Today",IF(D2<=TODAY()+7,"Due in 7 Days","Upcoming"))))
```

- **K2 (Month_Key)**
```excel
=TEXT(C2,"yyyy-mm")
```

- **L2 (Quarter_Key)**
```excel
=YEAR(C2)&"-Q"&ROUNDUP(MONTH(C2)/3,0)
```

Copy formulas down for all rows.

## 3) Row formulas (Zoho Sheet)

Zoho Sheet supports similar formulas. Use the same formulas, with this quarter alternative if needed:

- **L2 (Quarter_Key) - Zoho alternative**
```excel
=YEAR(C2)&"-Q"&INT((MONTH(C2)-1)/3)+1
```

> If your Zoho locale uses semicolons, replace commas with semicolons.

## 4) Report Sheet: `Reports`

Create a second sheet named **Reports**.

### 4.1 Monthly totals

- **Total invoiced for month** (cell B2, month key in A2 like `2026-02`):
```excel
=SUMIFS(Invoices!E:E,Invoices!K:K,A2)
```

- **Total collected for month**:
```excel
=SUMIFS(Invoices!F:F,Invoices!K:K,A2)
```

- **Total balance for month**:
```excel
=SUMIFS(Invoices!H:H,Invoices!K:K,A2)
```

### 4.2 Quarterly totals

- **Total invoiced for quarter** (cell E2, quarter key in D2 like `2026-Q1`):
```excel
=SUMIFS(Invoices!E:E,Invoices!L:L,D2)
```

- **Total collected for quarter**:
```excel
=SUMIFS(Invoices!F:F,Invoices!L:L,D2)
```

- **Total balance for quarter**:
```excel
=SUMIFS(Invoices!H:H,Invoices!L:L,D2)
```

### 4.3 Unpaid / Due / Overdue snapshots

- **Unpaid invoice count**:
```excel
=COUNTIFS(Invoices!G:G,"Unpaid")
```

- **Due today count**:
```excel
=COUNTIFS(Invoices!J:J,"Due Today")
```

- **Overdue count**:
```excel
=COUNTIFS(Invoices!J:J,"Overdue")
```

- **Overdue amount**:
```excel
=SUMIFS(Invoices!H:H,Invoices!J:J,"Overdue")
```

- **Due in next 7 days amount**:
```excel
=SUMIFS(Invoices!H:H,Invoices!J:J,"Due in 7 Days")
```

## 5) Comparative layout (Excel vs Zoho)

Use this mini table in `Reports`:

| Metric | Excel Formula | Zoho Formula |
|---|---|---|
| Month Invoiced | `=SUMIFS(Invoices!E:E,Invoices!K:K,A2)` | same |
| Quarter Invoiced | `=SUMIFS(Invoices!E:E,Invoices!L:L,D2)` | same |
| Unpaid Count | `=COUNTIFS(Invoices!G:G,"Unpaid")` | same |
| Overdue Amount | `=SUMIFS(Invoices!H:H,Invoices!J:J,"Overdue")` | same |
| Quarter Key | `=YEAR(C2)&"-Q"&ROUNDUP(MONTH(C2)/3,0)` | `=YEAR(C2)&"-Q"&INT((MONTH(C2)-1)/3)+1` |

## 6) Optional conditional formatting (both)

On `Invoices!J:J`:
- `Overdue` -> red fill
- `Due Today` -> orange fill
- `Due in 7 Days` -> yellow fill
- `Closed` -> green fill

This gives you quick visual reminders for due dates.
