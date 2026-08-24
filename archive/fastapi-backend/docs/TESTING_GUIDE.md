# WakaAgent AI - Testing Guide

## 🔐 Login Credentials

**Email**: `admin@example.com`  
**Password**: `admin123`

---

## 📋 Module Testing Checklist

This document provides comprehensive test scenarios and sample data for each module in the WakaAgent AI system.

---

## 1. 📊 Dashboard - Overview with Metrics

### Test Objectives
- Verify all KPI cards display correctly
- Check real-time data updates
- Validate chart rendering
- Test responsive layout

### Test Cases

#### TC-DASH-001: View Dashboard Metrics
**Steps:**
1. Login and navigate to Dashboard
2. Verify the following metrics are visible:
   - Total Revenue (current month)
   - Active Orders count
   - Total Customers count
   - Low Stock Alerts count

**Expected Results:**
- All KPI cards display with numerical values
- Charts render without errors
- Data refreshes on page load

#### TC-DASH-002: Recent Orders Widget
**Steps:**
1. Check "Recent Orders" section
2. Verify order details display correctly

**Sample Data to Verify:**
```json
{
  "order_id": "ORD-001",
  "customer": "Demo User 9486",
  "amount": "₦45,000",
  "status": "pending",
  "date": "2026-01-24"
}
```

#### TC-DASH-003: Sales Chart
**Steps:**
1. Locate the sales trend chart
2. Verify data points for the last 7 days
3. Check tooltip displays on hover

**Expected Results:**
- Line/bar chart displays sales data
- X-axis shows dates
- Y-axis shows revenue amounts
- Interactive tooltips work

---

## 2. 💬 Chat - AI Chat Interface

### Test Objectives
- Verify AI chat functionality
- Test voice transcription
- Validate multilingual support
- Check real-time message delivery

### Test Cases

#### TC-CHAT-001: Send Text Message
**Steps:**
1. Navigate to Chat module
2. Type a message in the input field
3. Click Send or press Enter

**Sample Messages to Test:**
```
"Show me today's orders"
"What products are low in stock?"
"Create a new customer named John Doe"
"What's the total revenue this month?"
```

**Expected Results:**
- Message appears in chat history
- AI responds within 3-5 seconds
- Response is relevant to the query

#### TC-CHAT-002: Voice Transcription
**Steps:**
1. Click the microphone icon
2. Allow microphone permissions
3. Speak a message
4. Click stop recording

**Sample Voice Commands:**
```
"How many orders do we have today?"
"Show me inventory status"
```

**Expected Results:**
- Audio is recorded successfully
- Transcription appears in the input field
- Message can be sent after transcription

#### TC-CHAT-003: Multilingual Support
**Steps:**
1. Select language from dropdown (Pidgin, Hausa, Yoruba, Igbo)
2. Send a message in the selected language

**Sample Messages:**
```
Pidgin: "How far, wetin be today sales?"
Hausa: "Ina kwana, yaya aiki?"
Yoruba: "Bawo ni, se alafia ni?"
Igbo: "Kedu ka ị mere?"
```

**Expected Results:**
- AI understands and responds in the same language
- Translation is contextually accurate

#### TC-CHAT-004: Intent Classification
**Steps:**
1. Send various types of requests
2. Verify correct agent routing

**Sample Intents:**
```
Orders: "Create a new order for customer ABC"
Inventory: "Check stock levels for Product XYZ"
CRM: "Add a new customer"
Finance: "Show me this month's revenue"
```

**Expected Results:**
- System routes to appropriate agent
- Response indicates correct intent understood

---

## 3. 🛒 Orders - Create and Manage Orders

### Test Objectives
- Create new orders
- Update order status
- Search and filter orders
- Generate order reports

### Test Cases

#### TC-ORD-001: Create New Order
**Steps:**
1. Navigate to Orders module
2. Click "Create Order" or "New Order" button
3. Fill in order details
4. Submit the order

**Sample Order Data:**
```json
{
  "customer_id": 1,
  "customer_name": "Demo User 9486",
  "items": [
    {
      "product_id": 1,
      "product_name": "Apple",
      "sku": "SKU-APPLE",
      "quantity": 50,
      "unit_price": 200,
      "subtotal": 10000
    },
    {
      "product_id": 2,
      "product_name": "Bread",
      "sku": "SKU-BREAD",
      "quantity": 20,
      "unit_price": 850,
      "subtotal": 17000
    }
  ],
  "subtotal": 27000,
  "tax": 2025,
  "total": 29025,
  "payment_method": "cash",
  "notes": "Deliver before 5 PM"
}
```

**Expected Results:**
- Order is created successfully
- Order ID is generated (e.g., ORD-12345)
- Inventory is reserved
- Order appears in orders list

#### TC-ORD-002: View Order Details
**Steps:**
1. Click on an existing order from the list
2. Verify all order information displays

**Expected Information:**
- Order ID and date
- Customer information
- Line items with quantities and prices
- Subtotal, tax, and total
- Payment status
- Fulfillment status

#### TC-ORD-003: Update Order Status
**Steps:**
1. Open an order with status "pending"
2. Change status to "processing"
3. Save changes

**Status Flow to Test:**
```
pending → processing → shipped → delivered → completed
```

**Expected Results:**
- Status updates successfully
- Timestamp is recorded
- Status history is maintained

#### TC-ORD-004: Fulfill Order
**Steps:**
1. Select an order with status "processing"
2. Click "Fulfill Order" button
3. Confirm fulfillment

**Expected Results:**
- Order status changes to "fulfilled"
- Inventory quantities are deducted
- Customer notification is sent (if configured)

#### TC-ORD-005: Search and Filter Orders
**Steps:**
1. Use search box to find orders by:
   - Order ID
   - Customer name
   - Date range
   - Status

**Sample Search Queries:**
```
"ORD-001"
"Demo User"
"2026-01-24"
Status: "pending"
```

**Expected Results:**
- Search returns relevant results
- Filters work correctly
- Results update in real-time

---

## 4. 👥 CRM - Customer Management

### Test Objectives
- Add new customers
- Update customer information
- View customer history
- Segment customers

### Test Cases

#### TC-CRM-001: Add New Customer
**Steps:**
1. Navigate to CRM module
2. Click "Add Customer" button
3. Fill in customer details
4. Save customer

**Sample Customer Data:**
```json
{
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "+234-801-234-5678",
  "location": "Lagos, Nigeria",
  "segment": "premium",
  "status": "active",
  "notes": "Prefers morning deliveries"
}
```

**Expected Results:**
- Customer is created with unique ID
- Customer appears in customer list
- All fields are saved correctly

#### TC-CRM-002: View Customer Profile
**Steps:**
1. Click on a customer from the list
2. Verify customer details display

**Expected Information:**
- Basic information (name, email, phone)
- Order history
- Total lifetime value
- Last order date
- Customer segment
- Notes and tags

#### TC-CRM-003: Update Customer Information
**Steps:**
1. Open customer profile
2. Click "Edit" button
3. Modify customer details
4. Save changes

**Sample Updates:**
```json
{
  "phone": "+234-802-987-6543",
  "segment": "vip",
  "notes": "Updated contact number"
}
```

**Expected Results:**
- Changes are saved successfully
- Update timestamp is recorded
- Audit log is created

#### TC-CRM-004: View Customer Order History
**Steps:**
1. Open customer profile
2. Navigate to "Orders" tab
3. Review order history

**Expected Results:**
- All customer orders are listed
- Orders show date, amount, and status
- Can click to view order details

#### TC-CRM-005: Customer Segmentation
**Steps:**
1. Filter customers by segment
2. Verify segment categories

**Segments to Test:**
```
- Regular
- Premium
- VIP
- Inactive
```

**Expected Results:**
- Customers are correctly categorized
- Segment filters work properly
- Count displays for each segment

---

## 5. 📦 Inventory - Stock Management

### Test Objectives
- View inventory levels
- Update stock quantities
- Track low stock alerts
- Manage warehouses

### Test Cases

#### TC-INV-001: View Inventory Dashboard
**Steps:**
1. Navigate to Inventory module
2. Review inventory overview

**Expected Information:**
- Total products count
- Low stock alerts count
- Out of stock items count
- Total inventory value

#### TC-INV-002: View Product Stock Levels
**Steps:**
1. View product list with stock information
2. Verify stock data displays correctly

**Sample Product Data:**
```json
{
  "product_id": 1,
  "sku": "SKU-APPLE",
  "name": "Apple",
  "warehouse": "Main",
  "on_hand": 100,
  "reserved": 25,
  "available": 75,
  "reorder_point": 50,
  "status": "in_stock"
}
```

**Expected Results:**
- All products display with stock levels
- Available quantity = On hand - Reserved
- Status indicators are correct (in stock, low stock, out of stock)

#### TC-INV-003: Update Stock Quantity
**Steps:**
1. Select a product
2. Click "Adjust Stock" or "Update Quantity"
3. Enter new quantity
4. Add reason for adjustment
5. Save changes

**Sample Adjustment:**
```json
{
  "product_id": 1,
  "adjustment_type": "addition",
  "quantity": 50,
  "reason": "New stock received",
  "warehouse_id": 1
}
```

**Expected Results:**
- Stock quantity is updated
- Adjustment is logged in history
- Available quantity recalculates

#### TC-INV-004: Low Stock Alerts
**Steps:**
1. View products with stock below reorder point
2. Verify alert notifications

**Expected Results:**
- Products with low stock are highlighted
- Alert badge shows count
- Can filter to show only low stock items

#### TC-INV-005: Stock Movement History
**Steps:**
1. Select a product
2. View "Stock History" or "Movements" tab
3. Review transaction history

**Expected Information:**
```
Date: 2026-01-24 10:30 AM
Type: Sale
Quantity: -10
Reference: ORD-001
New Balance: 90

Date: 2026-01-23 02:15 PM
Type: Adjustment
Quantity: +50
Reference: Stock Receipt #123
New Balance: 100
```

**Expected Results:**
- All stock movements are logged
- Shows date, type, quantity, and reference
- Running balance is maintained

---

## 6. 💰 Finance - Financial Reports

### Test Objectives
- View financial dashboard
- Generate sales reports
- Track receivables/payables
- Export financial data

### Test Cases

#### TC-FIN-001: View Financial Dashboard
**Steps:**
1. Navigate to Finance module
2. Review financial overview

**Expected Metrics:**
- Total Revenue (current month)
- Total Expenses
- Net Profit
- Outstanding Receivables
- Outstanding Payables
- Cash Flow

#### TC-FIN-002: Generate Daily Sales Report
**Steps:**
1. Select "Daily Sales Report"
2. Choose date range
3. Click "Generate Report"

**Sample Report Data:**
```json
{
  "report_date": "2026-01-24",
  "total_orders": 15,
  "total_revenue": 450000,
  "total_tax": 33750,
  "payment_methods": {
    "cash": 200000,
    "transfer": 150000,
    "card": 100000
  },
  "top_products": [
    {"name": "Apple", "quantity": 500, "revenue": 100000},
    {"name": "Bread", "quantity": 200, "revenue": 170000}
  ]
}
```

**Expected Results:**
- Report generates successfully
- All calculations are accurate
- Can export as CSV/PDF

#### TC-FIN-003: Monthly Audit Report
**Steps:**
1. Select "Monthly Audit Report"
2. Choose month and year
3. Generate report

**Expected Information:**
- Total sales by day
- Product performance
- Customer segments analysis
- Payment method breakdown
- AI insights and recommendations

#### TC-FIN-004: Manage Receivables (Debts)
**Steps:**
1. Navigate to "Receivables" or "Debts" section
2. View outstanding customer debts

**Sample Debt Record:**
```json
{
  "debt_id": 1,
  "customer_name": "Jane Smith",
  "amount": 50000,
  "due_date": "2026-02-01",
  "status": "pending",
  "days_overdue": 0,
  "order_reference": "ORD-123"
}
```

**Expected Results:**
- All debts are listed with details
- Can filter by status (pending, paid, overdue)
- Aging report shows days overdue

#### TC-FIN-005: Record Payment
**Steps:**
1. Select a debt record
2. Click "Record Payment"
3. Enter payment details
4. Save payment

**Sample Payment:**
```json
{
  "debt_id": 1,
  "amount": 25000,
  "payment_date": "2026-01-24",
  "payment_method": "bank_transfer",
  "reference": "TXN-789456",
  "notes": "Partial payment"
}
```

**Expected Results:**
- Payment is recorded
- Outstanding balance updates
- Payment history is maintained
- Status changes if fully paid

#### TC-FIN-006: Export Financial Data
**Steps:**
1. Generate any financial report
2. Click "Export" button
3. Choose format (CSV, Excel, PDF)
4. Download file

**Expected Results:**
- File downloads successfully
- Data is formatted correctly
- All columns are included
- UTF-8 encoding for special characters

---

## 7. 🎧 Support - Support Tickets

### Test Objectives
- Create support tickets
- Assign tickets to agents
- Update ticket status
- Track resolution time

### Test Cases

#### TC-SUP-001: Create Support Ticket
**Steps:**
1. Navigate to Support module
2. Click "New Ticket" button
3. Fill in ticket details
4. Submit ticket

**Sample Ticket Data:**
```json
{
  "customer_id": 1,
  "customer_name": "Demo User 9486",
  "subject": "Order delivery delayed",
  "description": "My order ORD-001 was supposed to arrive yesterday but hasn't been delivered yet.",
  "priority": "high",
  "category": "delivery",
  "status": "open"
}
```

**Expected Results:**
- Ticket is created with unique ID (e.g., TKT-001)
- Ticket appears in tickets list
- Customer is notified (if configured)
- Timestamp is recorded

#### TC-SUP-002: View Ticket Details
**Steps:**
1. Click on a ticket from the list
2. Review ticket information

**Expected Information:**
- Ticket ID and creation date
- Customer information
- Subject and description
- Priority and category
- Current status
- Assigned agent (if any)
- Conversation history

#### TC-SUP-003: Update Ticket Status
**Steps:**
1. Open a ticket
2. Change status
3. Add internal note or customer response
4. Save changes

**Status Flow to Test:**
```
open → in_progress → pending_customer → resolved → closed
```

**Expected Results:**
- Status updates successfully
- Status change is logged with timestamp
- Customer is notified of status changes

#### TC-SUP-004: Assign Ticket to Agent
**Steps:**
1. Open an unassigned ticket
2. Click "Assign" button
3. Select agent from dropdown
4. Save assignment

**Expected Results:**
- Ticket is assigned to selected agent
- Agent receives notification
- Assignment is logged in ticket history

#### TC-SUP-005: Add Response to Ticket
**Steps:**
1. Open a ticket
2. Type response in the reply field
3. Choose visibility (internal note or customer response)
4. Submit response

**Sample Response:**
```
"Hi [Customer Name],

Thank you for contacting us. I've checked your order ORD-001 and it's currently out for delivery. You should receive it by end of day today.

We apologize for the delay and appreciate your patience.

Best regards,
Support Team"
```

**Expected Results:**
- Response is added to ticket thread
- Timestamp and author are recorded
- Customer receives email notification (if public response)

#### TC-SUP-006: Filter and Search Tickets
**Steps:**
1. Use filters to find tickets by:
   - Status
   - Priority
   - Category
   - Assigned agent
   - Date range

**Sample Filters:**
```
Status: "open"
Priority: "high"
Category: "delivery"
Date: "Last 7 days"
```

**Expected Results:**
- Filters work correctly
- Multiple filters can be combined
- Results update in real-time

---

## 8. ⚙️ Admin - Admin Panel

### Test Objectives
- Manage users and roles
- Configure system settings
- View system logs
- Generate system reports

### Test Cases

#### TC-ADM-001: View User List
**Steps:**
1. Navigate to Admin module
2. Click "Users" section
3. Review user list

**Expected Information:**
- User ID
- Full name
- Email
- Role(s)
- Status (active/inactive)
- Last login date

#### TC-ADM-002: Create New User
**Steps:**
1. Click "Add User" button
2. Fill in user details
3. Assign role(s)
4. Save user

**Sample User Data:**
```json
{
  "email": "sales.agent@example.com",
  "full_name": "John Sales",
  "password": "SecurePass123!",
  "roles": ["Sales Representative"],
  "status": "active"
}
```

**Expected Results:**
- User is created successfully
- Password is hashed securely
- User can login with credentials
- User has appropriate permissions

#### TC-ADM-003: Manage User Roles
**Steps:**
1. Open user profile
2. View assigned roles
3. Add or remove roles
4. Save changes

**Available Roles:**
```
- Admin (full access)
- Sales (orders, customers)
- Ops (inventory, fulfillment)
- Finance (financial reports, debts)
- Sales Representative (limited sales access)
- Stock Keeper (inventory only)
```

**Expected Results:**
- Roles are updated successfully
- User permissions change accordingly
- Audit log records role changes

#### TC-ADM-004: View System Logs
**Steps:**
1. Navigate to "System Logs" or "Audit Logs"
2. Review recent activities

**Sample Log Entries:**
```
2026-01-24 10:30:15 | admin@example.com | LOGIN | Success
2026-01-24 10:31:42 | admin@example.com | CREATE_ORDER | ORD-001
2026-01-24 10:35:20 | admin@example.com | UPDATE_INVENTORY | Product ID: 1
2026-01-24 10:40:55 | admin@example.com | DELETE_DEBT | Debt ID: 5
```

**Expected Results:**
- All system activities are logged
- Shows timestamp, user, action, and entity
- Can filter by user, action type, or date
- Can export logs

#### TC-ADM-005: System Settings
**Steps:**
1. Navigate to "Settings" section
2. Review configuration options

**Settings to Verify:**
- Company information
- Tax rates
- Currency settings
- Email notifications
- Backup settings
- API keys (masked)

**Expected Results:**
- Settings display current values
- Can update settings
- Changes take effect immediately
- Sensitive data is masked

#### TC-ADM-006: Generate System Reports
**Steps:**
1. Select "System Reports"
2. Choose report type
3. Generate report

**Report Types:**
```
- User Activity Report
- System Performance Report
- Error Log Report
- Database Statistics
- API Usage Report
```

**Expected Results:**
- Reports generate successfully
- Data is accurate and up-to-date
- Can export in multiple formats

---

## 🔍 Cross-Module Integration Tests

### INT-001: Order to Inventory Flow
**Steps:**
1. Create an order with products
2. Check inventory levels before and after
3. Fulfill the order
4. Verify inventory deduction

**Expected Results:**
- Inventory is reserved when order is created
- Inventory is deducted when order is fulfilled
- Stock movements are logged

### INT-002: Customer to Orders to Finance Flow
**Steps:**
1. Create a new customer
2. Create an order for that customer
3. Mark order as debt (unpaid)
4. Check Finance module for receivable

**Expected Results:**
- Customer appears in CRM
- Order is linked to customer
- Debt record is created in Finance
- Customer debt balance updates

### INT-003: Chat to Action Flow
**Steps:**
1. Use Chat to create an order
2. Verify order appears in Orders module
3. Use Chat to check inventory
4. Verify data matches Inventory module

**Expected Results:**
- AI correctly executes actions
- Data is consistent across modules
- Real-time updates work

---

## 📊 Performance Testing

### PERF-001: Page Load Times
**Acceptance Criteria:**
- Dashboard loads in < 2 seconds
- Module pages load in < 1.5 seconds
- API responses in < 500ms

### PERF-002: Concurrent Users
**Test Scenario:**
- 10 users simultaneously accessing different modules
- All operations should complete without errors
- No significant performance degradation

### PERF-003: Large Dataset Handling
**Test Scenario:**
- 1000+ orders in database
- 500+ customers
- 200+ products
- Lists should paginate properly
- Search should remain responsive

---

## 🔒 Security Testing

### SEC-001: Authentication
**Tests:**
- Cannot access protected routes without login
- Invalid credentials are rejected
- Session expires after inactivity
- Logout clears session properly

### SEC-002: Authorization
**Tests:**
- Users can only access permitted modules
- Role-based access control works
- Cannot perform unauthorized actions
- API endpoints enforce permissions

### SEC-003: Data Validation
**Tests:**
- SQL injection attempts are blocked
- XSS attempts are sanitized
- CSRF protection is active
- Input validation works on all forms

---

## 📱 Responsive Design Testing

### RESP-001: Mobile View (320px - 767px)
**Test:**
- Sidebar collapses to hamburger menu
- Tables are scrollable or stacked
- Forms are usable on small screens
- Touch targets are appropriately sized

### RESP-002: Tablet View (768px - 1023px)
**Test:**
- Layout adapts appropriately
- Sidebar can be toggled
- All features remain accessible

### RESP-003: Desktop View (1024px+)
**Test:**
- Full sidebar is visible
- Multi-column layouts display correctly
- Charts and graphs scale properly

---

## 🐛 Bug Reporting Template

When reporting issues, use this format:

```markdown
**Bug ID:** BUG-XXX
**Module:** [Dashboard/Chat/Orders/CRM/Inventory/Finance/Support/Admin]
**Severity:** [Critical/High/Medium/Low]
**Priority:** [P0/P1/P2/P3]

**Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Result:**
[What should happen]

**Actual Result:**
[What actually happens]

**Environment:**
- Browser: [Chrome/Firefox/Safari]
- OS: [Windows/Mac/Linux]
- Screen Resolution: [1920x1080]

**Screenshots:**
[Attach screenshots if applicable]

**Console Errors:**
[Copy any console errors]
```

---

## ✅ Test Sign-Off Checklist

Before marking testing as complete, ensure:

- [ ] All modules are accessible
- [ ] CRUD operations work in each module
- [ ] Search and filter functions work
- [ ] Data validation is working
- [ ] Error messages are user-friendly
- [ ] Loading states display correctly
- [ ] Success messages appear
- [ ] No console errors
- [ ] Responsive design works
- [ ] Authentication and authorization work
- [ ] API integration is functional
- [ ] Real-time updates work (if applicable)
- [ ] Export functions work
- [ ] All test cases passed

---

## 📞 Support Contacts

**Technical Issues:**
- Backend: Check logs at `/Users/a/Documents/WakaAgentAI/backend/`
- Frontend: Check browser console (F12)

**Test Data Reset:**
- To reset test database, run: `alembic downgrade base && alembic upgrade head`

---

**Last Updated:** 2026-01-24  
**Version:** 1.0  
**Tested By:** CHIBUEZE AUGUSTINE
