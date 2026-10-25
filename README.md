# HCM Lite Backend (Python & FastAPI)

Foundation backend for **HCM Lite** built with Python 3.12, FastAPI, SQLAlchemy ORM, and MySQL following a strict `routes -> services -> models` architecture.

---

## 🏛️ Architecture (`routes -> services -> models`)

```
d:\hacktown\
├── .env.example              # MySQL configuration example (100% empty DB start)
├── .env                      # Active environment configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Uvicorn entry point
├── app/
│   ├── main.py               # FastAPI application, CORS, lifespan & error handlers
│   ├── core/
│   │   ├── config.py         # App configuration & DB URI normalization
│   │   ├── database.py       # SQLAlchemy engine, session maker, get_db dependency
│   │   ├── security.py       # bcrypt hashing, JWT access token generation & verification
│   │   └── audit_helper.py   # Reusable audit logging helper for AuditLog table
│   ├── middlewares/
│   │   ├── auth_middleware.py # JWT verification & user state attachment
│   │   └── rbac_middleware.py # RBAC validation & strict dataScope attachment
│   ├── models/               # SQLAlchemy Declarative Models
│   │   ├── organization.py   # Organization (office time, quotas, GPS, weekends)
│   │   ├── department.py     # Department (unique name, description)
│   │   ├── holiday.py        # Holiday (unique YYYY-MM-DD date, title)
│   │   ├── employee.py       # Employee model
│   │   ├── user.py           # User (Admin, HR, Employee, bcrypt password, FK employeeId)
│   │   └── audit_log.py      # Immutable AuditLog (actorId, role, action, entity, JSON before/after)
│   ├── schemas/              # Pydantic v2 validation & response models
│   │   ├── setup.py          # /api/setup schemas
│   │   ├── auth.py           # /api/auth schemas
│   │   └── org.py            # /api/org schemas
│   ├── services/             # Business Logic & Audit Log Recording
│   │   ├── setup_service.py
│   │   ├── auth_service.py
│   │   ├── org_service.py
│   │   ├── department_service.py
│   │   ├── holiday_service.py
│   │   └── hr_user_service.py
│   └── routes/               # FastAPI Routers
│       ├── setup_routes.py
│       ├── auth_routes.py
│       ├── org_routes.py
│       └── api_router.py     # Mounted under /api
└── tests/
    └── test_api.py           # Automated test suite covering Auth, RBAC, Setup & Org
```

---

## 🚀 Getting Started

### 1. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure MySQL is running. In `.env.example`:
```ini
DATABASE_URL="mysql://root:password@localhost:3306/hcm_lite"
```

> **Note**: Zero seed scripts or dummy data exist. The database starts 100% empty. All initial configuration occurs via `/api/setup/init`.

### 2. Install Dependencies
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Server
```bash
python run.py
```
API Documentation (Swagger UI): `http://localhost:5000/docs`

### 4. Run Test Suite
```bash
pytest
```

---

## 🔐 API Reference

### Module 1: Setup & Authentication
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/setup/status` | Public | Returns `{"isInitialized": false}` if 0 users exist in MySQL |
| `POST` | `/api/setup/init` | Public | One-time initialization. Creates Organization & initial Admin |
| `POST` | `/api/auth/login` | Public | Authenticates credentials, returns JWT & `mustChangePassword` |
| `POST` | `/api/auth/change-password` | Authenticated | Updates password and resets `mustChangePassword` to `false` |

### Module 2: Organization Setup & HR Management (Admin Only)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/org/settings` | Admin | Fetch company organization settings |
| `PUT` | `/api/org/settings` | Admin | Update organization settings (audited before/after) |
| `POST` | `/api/org/departments` | Admin | Create department (unique name) |
| `GET` | `/api/org/departments` | Admin | List all departments |
| `POST` | `/api/org/holidays` | Admin | Schedule holiday (YYYY-MM-DD, unique) |
| `GET` | `/api/org/holidays` | Admin | List all holidays sorted by date |
| `POST` | `/api/org/hr-users` | Admin | Create HR user account |
| `PATCH` | `/api/org/hr-users/{id}` | Admin | Deactivate/reactivate or reset password for HR user |

### Module 3: Employee Management & CSV Dry-Run Import
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/employees` | HR/Admin | Transactionally creates Employee with Org quotas & linked User with temp password |
| `GET` | `/api/employees` | HR/Admin | Server-side pagination (`page`, `limit`), search (`fullName`, `email`, `employeeCode`), & filters (`departmentId`, `status`) |
| `GET` | `/api/employees/{id}` | HR/Admin/Employee | 360 profile view. Employees strictly restricted to their own profile via `req.dataScope` |
| `PATCH` | `/api/employees/{id}` | HR/Admin/Employee | HR/Admin updates job/salary/status. Employees restricted to updating own `phone` and `address` only |
| `POST` | `/api/employees/csv-import` | HR/Admin | Supports `?dryRun=true\|false`. Validates all rows before importing to MySQL |

### Module 4: Attendance Management & Verification
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/attendance/check-in` | Employee | Server-timed check-in (ignores client clock). Returns 409 Conflict if already checked in today. Status 'late' if after `officeStartTime + graceMinutes`. Verifies GPS Haversine radius, accuracy <= 100m, and camera `facesDetectedCount === 1` |
| `POST` | `/api/attendance/check-out` | Employee | Server-timed check-out. Calculates `workedHours`. Updates status to `'half_day'` if `workedHours < halfDayHours` (5h) |
| `POST` | `/api/attendance/corrections` | Employee | Submits attendance correction request (`status: "Pending"`) |
| `PATCH` | `/api/attendance/corrections/{id}` | HR/Admin | Approves/rejects correction with HR comment. If approved, updates/creates Attendance and recalculates hours & status |

### Module 5: Leave Management & Quota Deductions
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/leaves` | Employee | Submits leave request. Calculates working days skipping weekends (Sat/Sun) and `Holiday` table dates. Returns 422 if dates overlap with Pending/Approved leaves, or if requested days exceed balance (except Unpaid) |
| `PATCH` | `/api/leaves/{id}/decision` | HR/Admin | Approves/rejects request with HR comment. If approved, atomically deducts `totalDays` from MySQL balance and records in `AuditLog` |

### Module 6: Payroll Lite
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/payroll/run` | HR/Admin | Generates or recalculates 'Draft' payslips for a given month (`YYYY-MM`). Blocked if already Finalized. |
| `POST` | `/api/payroll/{id}/finalize` | Admin | Locks payroll (`status = 'Finalized'`). Admin only. Triggers AuditLog and notifications for all employees. |
| `GET` | `/api/payroll/payslips` | HR/Admin/Employee | Lists payslips. HR/Admin sees all for month/employee; Employee sees only their own finalized payslips. |
| `GET` | `/api/payroll/payslips/{id}/pdf` | HR/Admin/Employee | Streams a clean PDF payslip generated on-the-fly with ReportLab (enforces employee `data_scope`). |

**Payroll Calculation Rules:**
- `HRA` = 40% of Basic, `Medical` = 10% of Basic, `Gross` = 1.5 * Basic (prorated by active working days if joined/exited mid-month).
- `perDayRate` = Gross / workingDaysInMonth.
- `deductionDays` = absentDays + unpaidLeaveDays + (0.5 * halfDays).
- `attendanceDeduction` = perDayRate * deductionDays.
- Progressive Tax Brackets on `annualGross = Gross * 12`:
  - Up to 600,000: 0%
  - 600,001 to 1,200,000: 5% of amount over 600,000
  - 1,200,001 to 2,400,000: 30,000 + 15% of amount over 1,200,000
  - 2,400,001 to 3,600,000: 210,000 + 25% of amount over 2,400,000
  - Above 3,600,000: 510,000 + 35% of amount over 3,600,000
  - Monthly tax = annualTax / 12.
- `netSalary` = max(0, Gross - attendanceDeduction - incomeTax).

### Module 7: Role-Based Analytics Dashboards
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/analytics/admin` | Admin | Total Headcount, Attrition Rate %, Dept Headcount breakdown, Monthly Payroll Cost trend, Recent Audit count. |
| `GET` | `/api/analytics/hr` | HR/Admin | Today's Attendance counts (present/late/absent/leave), Attendance Rate %, Late % by Dept, Absenteeism %, Leave Utilization %, Pending Approvals count. |
| `GET` | `/api/analytics/employee` | HR/Admin/Employee | Employee attendance summary for current month, Late count, Leave balances (Annual, Sick, Casual, Unpaid used), Latest Net Salary. |

### Module 8: AI Assistant with Tool Calling & Guardrails
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/ai/chat` | HR/Admin/Employee | AI chat with 7 RBAC-guarded tools (`get_headcount`, `get_attendance_summary`, `get_late_comers`, `get_leave_summary`, `get_my_leave_balance`, `get_payroll_summary`, `search_employees`). Enforces 20 req/hr rate limit and polite refusal guardrail when Employees query other users or organization-wide metrics. Every call logged in `AiLog`. |
| `POST` | `/api/ai/smart-leave` | HR/Admin/Employee | Accepts natural language text (e.g. "sick leave next Mon-Tue for doctor visit") and parses into structured JSON (`leaveType`, `startDate`, `endDate`, `reason`). |
| `POST` | `/api/ai/summarize-dashboard` | HR/Admin/Employee | Summarizes given metrics dictionary into a 3-4 bullet plain-English management digest. |

### Module 9: Announcements, Notifications & Audit Logs
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/announcements` | HR/Admin | Creates company-wide announcement. Audit logged. |
| `GET` | `/api/announcements` | All Authenticated | Lists all announcements ordered newest first. |
| `GET` | `/api/notifications` | All Authenticated | Lists user's own notifications. |
| `PATCH` | `/api/notifications/{id}/read` | All Authenticated | Marks owned notification as read. |
| `GET` | `/api/audit-logs` | Admin | Paginated audit log viewer with `beforeJSON` and `afterJSON` snapshots, filterable by `action` and `entity`. |

---

## 🛡️ Middlewares & RBAC Enforcement

- **`auth_middleware`**: Validates JWT bearer tokens, checks that user exists and is active, and attaches the user to `request.state.user`.
- **`rbac_middleware(allowed_roles)`**: Checks user role against permissions.
  - If role is `Employee`, strictly forces:
    ```python
    request.state.data_scope = {"employeeId": current_user.employeeId}
    ```
    preventing any employee from querying other users' data.
  - If role is `Admin` or `HR`, `request.state.data_scope = None`.
- **`audit_helper`**: Automatically records `CREATE`, `UPDATE`, `APPROVE`, `FINALIZE`, and `LOGIN` events into the immutable `AuditLog` table with JSON snapshots of `beforeJSON` and `afterJSON`.

