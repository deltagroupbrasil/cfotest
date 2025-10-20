#!/usr/bin/env python3
"""
Invoice Data Models
Separate from main transaction models to avoid conflicts
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

class InvoiceStatus(Enum):
    """Invoice processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"

class InvoiceType(Enum):
    """Invoice type classification"""
    PURCHASE = "purchase"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    UTILITY = "utility"
    OTHER = "other"

@dataclass
class InvoiceLineItem:
    """Individual line item in an invoice"""
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    tax_amount: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total': float(self.total),
            'tax_amount': float(self.tax_amount) if self.tax_amount else None
        }

@dataclass
class InvoiceVendor:
    """Vendor information"""
    name: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'address': self.address,
            'tax_id': self.tax_id,
            'email': self.email,
            'phone': self.phone
        }

@dataclass
class Invoice:
    """
    Main Invoice model - Isolated from main system
    Maps to 'invoices' table, separate from 'transactions'
    """
    # Required fields
    invoice_number: str
    date: date
    vendor: InvoiceVendor
    total_amount: Decimal
    currency: str = "USD"

    # Optional fields
    id: Optional[str] = None
    due_date: Optional[date] = None
    tax_amount: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    line_items: List[InvoiceLineItem] = None
    payment_terms: Optional[str] = None

    # Processing metadata
    status: InvoiceStatus = InvoiceStatus.PENDING
    invoice_type: InvoiceType = InvoiceType.OTHER
    confidence_score: float = 0.0
    processing_notes: Optional[str] = None

    # Source tracking
    source_file: Optional[str] = None
    email_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime = None

    # Integration with main system
    business_unit: Optional[str] = None  # Maps to main system entities
    category: Optional[str] = None       # Expense category

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.line_items is None:
            self.line_items = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'date': self.date.isoformat() if self.date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'vendor': self.vendor.to_dict(),
            'total_amount': float(self.total_amount),
            'currency': self.currency,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'subtotal': float(self.subtotal) if self.subtotal else None,
            'line_items': [item.to_dict() for item in self.line_items],
            'payment_terms': self.payment_terms,
            'status': self.status.value,
            'invoice_type': self.invoice_type.value,
            'confidence_score': self.confidence_score,
            'processing_notes': self.processing_notes,
            'source_file': self.source_file,
            'email_id': self.email_id,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat(),
            'business_unit': self.business_unit,
            'category': self.category
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """Create Invoice from dictionary"""
        vendor = InvoiceVendor(**data.get('vendor', {}))

        line_items = []
        for item_data in data.get('line_items', []):
            line_items.append(InvoiceLineItem(
                description=item_data.get('description', ''),
                quantity=Decimal(str(item_data.get('quantity', 0))),
                unit_price=Decimal(str(item_data.get('unit_price', 0))),
                total=Decimal(str(item_data.get('total', 0))),
                tax_amount=Decimal(str(item_data.get('tax_amount', 0))) if item_data.get('tax_amount') else None
            ))

        return cls(
            id=data.get('id'),
            invoice_number=data['invoice_number'],
            date=datetime.fromisoformat(data['date']).date() if data.get('date') else None,
            due_date=datetime.fromisoformat(data['due_date']).date() if data.get('due_date') else None,
            vendor=vendor,
            total_amount=Decimal(str(data['total_amount'])),
            currency=data.get('currency', 'USD'),
            tax_amount=Decimal(str(data['tax_amount'])) if data.get('tax_amount') else None,
            subtotal=Decimal(str(data['subtotal'])) if data.get('subtotal') else None,
            line_items=line_items,
            payment_terms=data.get('payment_terms'),
            status=InvoiceStatus(data.get('status', 'pending')),
            invoice_type=InvoiceType(data.get('invoice_type', 'other')),
            confidence_score=data.get('confidence_score', 0.0),
            processing_notes=data.get('processing_notes'),
            source_file=data.get('source_file'),
            email_id=data.get('email_id'),
            processed_at=datetime.fromisoformat(data['processed_at']) if data.get('processed_at') else None,
            created_at=datetime.fromisoformat(data['created_at']),
            business_unit=data.get('business_unit'),
            category=data.get('category')
        )

    def is_valid(self) -> bool:
        """Validate invoice data"""
        return (
            bool(self.invoice_number) and
            bool(self.vendor.name) and
            self.total_amount > 0 and
            bool(self.currency) and
            self.date is not None
        )

    def get_classification_hint(self) -> str:
        """Get hint for business unit classification based on vendor"""
        vendor_lower = self.vendor.name.lower()

        # Technology expenses
        if any(tech in vendor_lower for tech in ['aws', 'google', 'microsoft', 'software', 'saas']):
            return 'Delta LLC'

        # Paraguay operations
        if any(py in vendor_lower for py in ['paraguay', 'asuncion', 'ande']):
            return 'Delta Mining Paraguay S.A.'

        # Brazil operations
        if any(br in vendor_lower for br in ['brasil', 'brazil', 'porto seguro']):
            return 'Delta Brazil'

        # Default to main entity
        return 'Delta LLC'