# ACE Mart System — Python + Flask

ACE Mart is an e-commerce platform designed to simulate international snack retail operations. Built using Python, Flask, and SQLite, the codebase translates UML class diagrams into a fully interactive web application, adhering to object-oriented principles, design patterns, and clean architecture guidelines.

---

## Architecture & Project Structure

The codebase is organized into modular domain components under the `models/` directory. For demonstration and standalone testing, a unified package-free implementation containing all domain logic is maintained in `all_classes.py`.

```text
Software-Architecture-Assignment-3/
├── app.py                      # Flask web application server, seed data, and API routes
├── all_classes.py              # Standalone single-file version of all domain classes
├── requirements.txt            # Python dependencies
├── acemart.db                  # SQLite database (auto-generated on startup)
├── models/                     # Domain class modules
│   ├── __init__.py             # Re-exports domain classes
│   ├── account.py              # Base Account model
│   ├── account_factory.py      # Factory Pattern implementation
│   ├── customer.py             # Customer model (extends Account)
│   ├── admin.py                # Admin model (extends Account)
│   ├── manager.py              # Manager model (Singleton orchestrator)
│   ├── report.py               # Report entity
│   ├── product.py              # Product entity (manages inventory states and signaling)
│   ├── category.py             # Category entity (groups products)
│   ├── catalogue.py            # Catalogue entity (aggregates categories)
│   ├── shopping_cart.py        # CartItem & ShoppingCart (Composition)
│   ├── order.py                # Order state manager
│   ├── invoice.py              # Invoice entity (calculates and stores grand totals)
│   ├── payment_gateway.py      # Strategy Pattern interface (CreditCard vs EWallet)
│   ├── payment.py              # Payment processing model
│   ├── shipment.py             # Shipment logistical model
│   ├── feedback.py             # Feedback entity
│   └── support_ticket.py       # SupportTicket entity
└── templates/                  # Jinja2 HTML templates
    ├── store.html              # Main storefront, search, and catalog navigation
    ├── cart.html               # Customer cart adjustments, address management, and checkout triggers
    ├── payment.html            # Secure payment simulation portal
    ├── orders.html             # Customer order history and feedback forms
    ├── invoice.html            # Printable paper-style invoice display
    ├── support.html            # Help ticket generation and resolution reopening
    ├── profile.html            # Profile management and credential updates
    └── admin.html              # Staff & Manager operational dashboard
```

---

## Design Patterns

| Pattern | Module | Description |
| :--- | :--- | :--- |
| **Factory** | `AccountFactory` | Instantiates specialized `Customer` or `Admin` instances dynamically based on type parameters, abstracting password hashing steps and ID assignments. |
| **Singleton** | `Manager` | Serves as the central access point for product collections, active orders, reporting routines, and administrative signaling. |
| **Strategy** | `PaymentGateway` | Establishes an abstract strategy for transaction processing, executed by concrete variants: `CreditCardGateway` and `EWalletGateway`. |
| **Composition** | `Customer` ◆— `ShoppingCart` | Establishes a strict composition relationship; the lifecycle of the shopping cart is directly bound to its parent `Customer` instance. |
| **Aggregation** | `Catalogue` ◇— `Category` ◇— `Product` | Leverages loose lifecycle aggregation; products can exist independently of individual categories or catalogs. |

---

## Architectural Heuristics

*   **Heuristic 2.9 (Cohesion)**: Handled directly within class boundaries. For example, `Product.reduce_stock` self-evaluates current inventory counts, executes safe modifications, and proactively registers low-stock notifications with the central `Manager` when levels fall below standard operating thresholds (10 units).
*   **Heuristic 5.1 (Role-Based Access Control / RBAC)**: Decoupled role handling is validated inside `app.py` via route decorators (`@login_required_customer`, `@login_required_admin`) and parsed in UI templates to partition views between standard Customers, operational Store Staff, and the coordinating Manager.
*   **Coupling Reduction (Riel Heuristic)**: Rather than establishing tight structural coupling across multiple reporting entities, the `Manager` singleton aggregates reporting data (such as turnover ratios and sales summaries) by traversing the active `Order` collection. This prevents direct, rigid dependencies on secondary entities like `Invoice` or `Feedback`.

---

## Setup & Execution

### Prerequisites
*   Python 3.8 or higher
*   pip (Python package installer)

### Quick Start
1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Flask Application**:
    ```bash
    python app.py
    ```
    *The terminal will display the local development address (typically `http://127.0.0.1:5000`). Access this URL in your browser.*
    *Upon startup, the system automatically checks for the existence of `acemart.db`. If missing, the database is created, schema initialized, and standard seed profiles are generated. On subsequent runs, state is reloaded from the database automatically.*

    * **💡 Developer Tip (System Reset):** If you want to reset the store back to its original, fresh seeded state (original stock levels, default credentials, and empty order histories) at any point during your testing, simply delete the `acemart.db` file from your project root and restart the server. The application will automatically detect the missing database, recreate the SQL schema, and re-seed the default state instantly.

3.  **Run the Standalone Domain Demo**:
    To run a terminal-only demonstration of the domain class interactions without launching the Flask server:
    ```bash
    python all_classes.py
    ```

---

## Seed Accounts

The database comes pre-seeded with three reference accounts representing distinct roles within the platform:

| Role | Email Address | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Customer** | `alex@acemart.com` | `pw1234` | Cart operations, checkout, address book management, transaction simulation, orders log, support requests, and feedback reviews. |
| **Store Staff** | `lee@acemart.com` | `staff123` | Product additions, category administration, inventory adjustments, order transition processing, and support ticket resolution. |
| **Manager** | `sam@acemart.com` | `admin123` | KPI review, ticket assignments, real-time report compilation (turnover analysis, category sales breakdown, and performance reviews). |

---

## Role Operations & Platform Capabilities

### Shopper Portal (Customer)
*   **Catalog Search & Filtering**: Navigate active categories and filter specific snack items. Inactive categories and products are hidden from search lists.
*   **Cart & Address Book**: Adjust item quantities (capped at current available inventory levels), manage multiple shipping destinations, and select active delivery targets.
*   **Order & Payment Simulation**: Place orders to generate invoices. The secure payment page allows selecting card or e-wallet methods, supporting both successful payments and mock validation declines.
*   **Order Tracker & Invoices**: Monitor order progress (Pending, Processing, Shipped, Delivered) and access a printable paper-style invoice.
*   **Customer Care**: Submit support tickets tied to specific orders, reopen resolved cases if needed, and leave star reviews once delivery is confirmed.

### Store Staff Portal (Admin)
*   **Product Operations**: Add products, replenish inventory, and toggle catalog visibility (soft-deleting products to protect past order histories).
*   **Category Controls**: Create and rename categories, or toggle category activation states in real-time.
*   **Order Processing**: Progress order lifecycles through manual transitions (`Accept` → `Ship` → `Deliver` → `Cancel` → `Refund`). Dispatched shipments require carrier details and tracking identifiers.
*   **Resolution Center**: View open support tickets and submit resolution notes.
*   **Staff Alerts**: Bell icon notification dropdown displays updates for low-stock indicators ($\le 10$ units), new customer orders, and reviews.

### Manager Portal (Admin + Elevated Access)
*   **Consolidated Dashboard**: Displays visual analytics compiled using Chart.js, rendering five charts for product stock levels, category sales distribution, order status ratios, feedback ratings, and ticket statuses.
*   **Reporting Suite**: Request and compile reports. The system dynamically isolates database records to target specific time horizons (e.g., Last 24 Hours, Last 7 Days, Last 30 Days) to compute:
    *   *Inventory Turnover Rate* (Units sold vs. average inventory level).
    *   *Top-Selling & Low-Performing Items*.
    *   *Category Sales Revenue*.
*   **Staff Coordination Loop**: Receive real-time administrative notification flags when operational staff members send requests for report updates.

---

## HTTP API Route Directory

### Authentication & Session Management
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Guest | Authenticates credentials and starts the session. Accepts `email`, `password`, and optional `role` field (`customer` or `admin`). |
| `POST` | `/api/auth/signup` | Guest | Registers a new Customer profile. Requires `username`, `email`, `password` (min 6 chars), and `address`. |
| `POST` | `/api/profile/password/reset` | Authenticated | Validates `current_password` against the stored hash and updates to `new_password` (min 6 chars). |
| `POST` | `/api/customer/profile/update` | Authenticated | Updates `username` and (for Customer accounts) `phone` on the logged-in profile. |
| `GET` | `/logout` | Authenticated | Clears the active session and redirects to the storefront. |

### Cart Operations
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/cart` | Customer | Retrieves the current shopping cart itemization and totals. Returns an empty cart for unauthenticated requests. |
| `POST` | `/api/cart/add` | Customer | Adds a `quantity` of a `product_id` to the cart. Validates stock availability against the Catalogue. |
| `POST` | `/api/cart/update` | Customer | Modifies item `quantity` for a `product_id`, validated against available stock. Removes the item if quantity ≤ 0. |
| `POST` | `/api/cart/remove` | Customer | Removes a `product_id` entry from the active cart. |
| `POST` | `/api/cart/checkout` | Customer | Snapshots the cart into a pending Order, generates an invoice, and triggers a staff notification. Returns `order_id` and `total` (including shipping). Does not reduce stock until payment is confirmed. |

### Address Book Management
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/customer/addresses` | Customer | Returns the customer's full address list and the currently active shipping address. |
| `POST` | `/api/customer/addresses/add` | Customer | Appends a new `address` to the profile. Automatically sets it as active if no address exists yet. |
| `POST` | `/api/customer/addresses/select` | Customer | Sets an existing `address` as the active shipping destination. |
| `POST` | `/api/customer/addresses/edit` | Customer | Updates an entry by replacing `old_address` with `new_address`. Updates the active address if it was the one edited. |
| `POST` | `/api/customer/addresses/delete` | Customer | Removes an `address` from the book. Resets the active address to the next available entry. |

### Transactions & Logistics
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/payment/process` | Customer | Processes payment for an `order_id` via the Strategy Pattern. Accepts `gateway` (`credit_card` or `ewallet`), relevant card/wallet fields, and an optional `simulate_failure` boolean to test decline flows. On success, reduces inventory stock and clears the cart. |

### Customer Notifications
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/customer/notifications` | Customer | Returns the customer's order status update notifications and current `unread_count`. |
| `POST` | `/api/customer/notifications/read` | Customer | Marks all customer notifications as read. |

### Feedback & Support Tickets
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/feedback` | Public | Returns all feedback entries across all orders. |
| `POST` | `/api/feedback` | Customer | Submits a `rating` (1–5) and `comment` for a delivered `order_id`. Only one feedback entry is allowed per order. Triggers a staff notification. |
| `GET` | `/api/tickets` | Customer | Returns all support tickets raised by the logged-in customer. |
| `POST` | `/api/tickets` | Customer | Creates a new support ticket with `subject`, `description`, and optional `order_id` to associate it with a specific order. Triggers a staff notification. |
| `POST` | `/api/tickets/reopen` | Customer | Reopens a resolved ticket by `ticket_id`. Only the owning customer may reopen their own ticket. |

### General Data Endpoints
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/products` | Public | Returns the full product list from the Manager registry. |
| `GET` | `/api/orders` | Public | Returns all orders from the Manager registry. |

### Operational Administration (Store Staff)
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/admin/product/add` | Admin (Staff) | Adds a new product with `name`, `description`, `price`, `stock`, `category_id`, and `emoji` to the catalog. |
| `POST` | `/api/admin/product/restock` | Admin (Staff) | Adds `quantity` units to an existing `product_id`. |
| `POST` | `/api/admin/product/toggle_active` | Admin (Staff) | Toggles the public catalog visibility (`is_active`) of a `product_id`. |
| `POST` | `/api/admin/product/remove` | Admin (Staff) | Permanently removes a `product_id` from the Manager registry and all categories. |
| `POST` | `/api/admin/category/add` | Admin (Staff) | Registers a new category with `name` and optional `description`. Rejects duplicate category names. |
| `POST` | `/api/admin/category/rename` | Admin (Staff) | Updates the `name` of an existing `category_id`. |
| `POST` | `/api/admin/category/toggle_active` | Admin (Staff) | Toggles public catalog visibility for all products within a `category_id`. |
| `POST` | `/api/admin/order/accept` | Admin (Staff) | Accepts a pending order (`Pending` → `Processing`) and sends a customer notification. |
| `POST` | `/api/admin/order/ship` | Admin (Staff) | Dispatches an order with `carrier` and `tracking_number` details (`Processing` → `Shipped`). Notifies the customer. |
| `POST` | `/api/admin/order/deliver` | Admin (Staff) | Confirms delivery (`Shipped` → `Delivered`) and prompts the customer to leave a review. |
| `POST` | `/api/admin/order/cancel` | Admin (Staff) | Cancels an order, restores inventory stock levels for all items, and notifies the customer. |
| `POST` | `/api/admin/order/refund` | Admin (Staff) | Processes a refund for a cancelled or delivered order. Restores stock if the order was not already cancelled. Cannot refund orders in `shipped` status. |
| `POST` | `/api/admin/ticket/resolve` | Admin (Staff) | Submits resolution `notes` to close a support ticket by `ticket_id`. |

### System Reports & Manager Workflows
| Method | Path | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/admin/report/<type>` | Admin | Retrieves or compiles a report. `<type>` must be one of: `inventory`, `orders`, `sales`, `feedback`, or `support`. Accepts optional `period` query param (`day`, `week`, `month`, `year`, `ytd`, `all`) and a `compile=true` flag (Manager only) to generate a fresh version. Staff can only view the latest Manager-compiled report. |
| `POST` | `/api/admin/report/request` | Admin (Staff) | Sends a report compilation request notification to the Manager. Requires `report_type` in the request body. |
| `POST` | `/api/admin/ticket/assign` | Admin (Manager) | Assigns a support ticket (`ticket_id`) to a staff member (`assignee_id`). Manager role only. |
| `GET` | `/api/admin/notifications` | Admin | Returns role-appropriate notifications: Managers receive manager-level alerts; Staff receive operational alerts (orders, low stock, new reviews). Includes `unread_count`. |
| `POST` | `/api/admin/notifications/read` | Admin | Marks all role-appropriate notifications as read. |
