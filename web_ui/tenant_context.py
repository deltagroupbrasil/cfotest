#!/usr/bin/env python3
"""
Tenant Context Manager for Multi-Tenant SaaS
Handles tenant identification and session management
"""

from flask import session, g, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Default tenant (for backward compatibility)
DEFAULT_TENANT_ID = 'delta'

def get_current_tenant_id() -> str:
    """
    Get the current tenant ID from session or default to 'delta'

    Priority:
    1. Flask g object (set per request)
    2. Flask session (persists across requests)
    3. Request header (X-Tenant-ID for API calls)
    4. Default tenant 'delta'

    Returns:
        str: Tenant ID
    """
    try:
        # Check Flask g object first (set per request)
        if hasattr(g, 'tenant_id'):
            return g.tenant_id

        # Check session
        if 'tenant_id' in session:
            tenant_id = session['tenant_id']
            g.tenant_id = tenant_id  # Cache in g
            return tenant_id

        # Check request header for API calls
        if request:
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                g.tenant_id = tenant_id
                return tenant_id

        # Default to 'delta' for backward compatibility
        tenant_id = DEFAULT_TENANT_ID
        g.tenant_id = tenant_id
        return tenant_id

    except RuntimeError:
        # Outside of Flask application context - return default
        return DEFAULT_TENANT_ID

def set_tenant_id(tenant_id: str):
    """
    Set the current tenant ID in session

    Args:
        tenant_id: Tenant identifier
    """
    session['tenant_id'] = tenant_id
    g.tenant_id = tenant_id
    logger.info(f"Tenant context set to: {tenant_id}")

def clear_tenant_id():
    """
    Clear the tenant ID from session (reset to default)
    """
    if 'tenant_id' in session:
        del session['tenant_id']
    if hasattr(g, 'tenant_id'):
        delattr(g, 'tenant_id')
    logger.info("Tenant context cleared (reset to default)")

def require_tenant(f):
    """
    Decorator to ensure tenant_id is set before executing a function

    Usage:
        @app.route('/api/transactions')
        @require_tenant
        def get_transactions():
            tenant_id = get_current_tenant_id()
            # ... query with tenant_id filter
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = get_current_tenant_id()

        if not tenant_id:
            return {
                'error': 'Tenant context not set',
                'message': 'Please set tenant_id in session or X-Tenant-ID header'
            }, 400

        logger.debug(f"Request processing for tenant: {tenant_id}")
        return f(*args, **kwargs)

    return decorated_function

def init_tenant_context(app):
    """
    Initialize tenant context for Flask app

    This sets up before_request handlers to ensure tenant_id is always available

    Args:
        app: Flask application instance
    """
    @app.before_request
    def set_tenant_context():
        """
        Before each request, ensure tenant_id is available in g
        """
        tenant_id = get_current_tenant_id()
        g.tenant_id = tenant_id

        # Log tenant context for debugging (only in development)
        if app.debug:
            logger.debug(f"Request: {request.method} {request.path} | Tenant: {tenant_id}")

    @app.after_request
    def add_tenant_header(response):
        """
        Add tenant ID to response headers for debugging
        """
        if hasattr(g, 'tenant_id'):
            response.headers['X-Current-Tenant'] = g.tenant_id
        return response

    logger.info("Tenant context initialized for Flask app")

# Convenience function for database queries
def get_tenant_filter() -> dict:
    """
    Get a dictionary filter for database queries

    Returns:
        dict: {'tenant_id': 'current_tenant'}

    Usage:
        query = "SELECT * FROM transactions WHERE tenant_id = %s AND date = %s"
        tenant_id = get_current_tenant_id()
        results = db.execute(query, (tenant_id, date))
    """
    return {'tenant_id': get_current_tenant_id()}

def build_tenant_query_params(*additional_params):
    """
    Build query parameters tuple starting with tenant_id

    Args:
        *additional_params: Additional query parameters

    Returns:
        tuple: (tenant_id, *additional_params)

    Usage:
        params = build_tenant_query_params(date, amount)
        # Returns: ('delta', '2024-10-14', 100.00)
    """
    return (get_current_tenant_id(),) + additional_params
