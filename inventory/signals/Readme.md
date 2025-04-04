## Overview

The system uses Django signals to maintain consistency between different models and ensure data integrity. It handles various business operations:

- Purchase management (adding inventory)
- Sales management (reducing inventory and managing customer credit)
- Stock transfers between shops
- Receipt handling (payments against sales invoices)
- Average cost calculations for inventory valuation
- Customer credit tracking and management

## Core Modules

### 1. Receipt Signals (`receipt_signals.py`)

Handles all financial aspects of receipt creation, updates, and deletion.

**Key Scenarios Covered:**
- Creating new receipts (updating account balances and customer credits)
- Changing receipt amounts or accounts
- Moving receipts between invoices
- Deleting receipts (reversing all financial effects)

**Flow:**
```
Receipt Created → Account Balance ↑ → Invoice Paid Amount ↑ → Customer Credit ↓
```

### 2. Sales Signals (`sale_signals.py`)

Manages inventory reductions and customer credit when products are sold.

**Key Scenarios Covered:**
- Stock reduction on new sales
- Customer credit increases for unpaid invoices
- Quantity and price changes affecting customer credit
- Product changes in sales items
- Customer changes for entire invoices
- Shop changes for entire invoices
- Returning stock when sales are deleted
- Adjusting customer credit when items or invoices are deleted

**Flow:**
```
Sale Created → Shop Stock ↓ → Customer Credit ↑
Payment Received → Customer Credit ↓
```

### 3. Purchase Signals (`purchase_signals.py`)

Handles inventory increases and average cost calculations for purchases.

**Key Scenarios Covered:**
- Adding stock on new purchases
- Calculating weighted average costs
- Handling quantity and price changes
- Product changes in purchase items
- Shop changes for entire invoices
- Reverting stock when purchases are deleted

**Flow:**
```
Purchase Created → Shop Stock ↑ → Average Cost Recalculated
```

### 4. Stock Transfer Signals (`stock_transfer_signals.py`)

Manages movement of inventory between shops with proper cost tracking.

**Key Scenarios Covered:**
- Transferring stock between shops
- Maintaining average costs during transfers
- Handling quantity changes in transfer items
- Product changes in transfer items
- Shop changes for entire transfers
- Reverting transfers when deleted

**Flow:**
```
Transfer Created → Source Shop Stock ↓ → Destination Shop Stock ↑ → Average Cost Transferred
```

## Customer Credit Management

The system maintains accurate customer credit throughout all sales and payment operations.

### Credit Flow:
```
Sales Invoice Created → Customer Credit ↑ (by unpaid amount)
Receipt Created → Customer Credit ↓ (by payment amount)
Invoice Updated → Customer Credit Adjusted (based on changes)
Invoice Deleted → Customer Credit ↓ (by unpaid amount)
```

### Credit Scenarios Handled:
- Customer changes on invoices (moves credit between customers)
- Price or quantity changes on items (adjusts credit accordingly)
- Item additions or deletions (increases or decreases credit)
- Customer deletion (handles orphaned credit)
- Partial payments (tracks remaining credit accurately)

## Average Cost Calculation

The system maintains accurate weighted average costs throughout all inventory operations.

### Purchase Example:
```
Initial:  10 units at $50 = $500 total value
Purchase: 5 units at $60 = $300 new value
Result:   15 units at $53.33 = $800 total value

Calculation: ($500 + $300) ÷ 15 = $53.33
```

### Transfer Example:
```
Shop 1: 20 units at $40 = $800 total value
Shop 2: 5 units at $30 = $150 total value
Transfer: 8 units from Shop 1 to Shop 2

Result Shop 1: 12 units at $40 (avg cost unchanged)
Result Shop 2: 13 units at $36.15

Calculation for Shop 2: ($150 + $40×8) ÷ (5 + 8) = $36.15
```

## Key Features

### 1. Data Integrity
- All operations are wrapped in transactions
- Original values are stored before updates
- Proper reversal of effects when items are deleted

### 2. Accurate Financial Tracking
- Weighted average cost calculations
- Customer credit management
- Value movement tracking during transfers
- Prevention of division by zero errors

### 3. Shop Management
- Multi-shop inventory tracking
- Cross-shop transfers with cost inheritance
- Shop change handling for invoices

### 4. Customer Management
- Credit tracking for customers
- Credit transfers when customers change
- Handling of credit adjustments for all invoice operations

### 5. Comprehensive Logging
- Detailed logging of all operations
- Warnings for insufficient stock
- Error logging for debugging
- Financial transaction logging

### 6. Edge Case Handling
- Negative quantity prevention
- Insufficient stock warnings
- Missing stock record creation
- Product and shop changes
- Customer changes

## Implementation Details

### Signal Usage
- `pre_save`: Stores original values before changes
- `post_save`: Processes changes and updates related records
- `pre_delete`: Prepares for deletion and stores necessary data
- `post_delete`: Finalizes cleanup after deletion

### Transaction Management
All related changes are wrapped in `transaction.atomic()` blocks to ensure consistency even if errors occur.

### Stock Changes
Stock quantity changes follow these guidelines:
- Stock can never be negative (set to 0 if would go negative)
- Insufficient stock generates warnings but doesn't prevent operations
- Creating/removing stock records as needed

### Credit Management
Customer credit changes follow these guidelines:
- Credit increases when sales are created
- Credit decreases when payments are received
- Credit moves between customers when invoices change customers
- Credit adjusts when invoice amounts change

## Logging and Monitoring

The system includes comprehensive logging at different levels:
- `INFO`: Normal operations like stock movements and credit changes
- `WARNING`: Potential issues like insufficient stock
- `ERROR`: Problems like missing records or calculation errors
- `DEBUG`: Detailed tracking for development and debugging

## Edge Cases and Solutions

| Edge Case | Solution |
|-----------|----------|
| Shop change in invoice | Return stock to original shop, reduce from new shop |
| Customer change in invoice | Move credit from original customer to new customer |
| Product change in item | Return stock for original product, reduce for new product |
| Insufficient stock | Allow operation but log warning |
| Division by zero | Prevent with checks, keep existing average cost |
| Negative stock | Set quantity to zero and log warning |
| Missing stock records | Create new records when needed |
| Deleting partially paid invoice | Adjust customer credit only by unpaid amount |

## Conclusion

This system provides robust inventory and financial management with accurate cost tracking and customer credit management. It handles a wide range of business scenarios and maintains data integrity across all operations through careful transaction management and comprehensive signals architecture.