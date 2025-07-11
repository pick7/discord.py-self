"""
The MIT License (MIT)

Copyright (c) 2021-present Dolfies

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from .billing import PaymentSource
from .enums import (
    PaymentGateway,
    PaymentStatus,
    RefundDisqualificationReason,
    SubscriptionType,
    try_enum,
)
from .flags import PaymentFlags
from .mixins import Hashable
from .store import SKU
from .subscriptions import Subscription
from .utils import _get_as_snowflake, parse_time

if TYPE_CHECKING:
    from .state import ConnectionState
    from .types.payments import Payment as PaymentPayload

__all__ = ('Payment', 'BRAINTREE_KEY', 'STRIPE_KEY', 'ADYEN_KEY')

BRAINTREE_KEY = 'production_ktzp8hfp_49pp2rp4phym7387'
STRIPE_KEY = 'pk_live_CUQtlpQUF0vufWpnpUmQvcdi'
ADYEN_KEY = 'live_E3OQ33V6GVGTXOVQZEAFQJ6DJIDVG6SY'


class Payment(Hashable):
    """Represents a payment to Discord.

    .. container:: operations

        .. describe:: x == y

            Checks if two payments are equal.

        .. describe:: x != y

            Checks if two payments are not equal.

        .. describe:: hash(x)

            Returns the payment's hash.

        .. describe:: str(x)

            Returns the payment's description.

    .. versionadded:: 2.0

    .. versionchanged:: 2.1

        Removed the ``refund()`` method due to an API change.

    Attributes
    ----------
    id: :class:`int`
        The ID of the payment.
    amount: :class:`int`
        The amount of the payment.
    amount_refunded: :class:`int`
        The amount refunded from the payment, if any.
    tax: :class:`int`
        The amount of tax paid.
    tax_inclusive: :class:`bool`
        Whether the amount is inclusive of all taxes.
    currency: :class:`str`
        The currency the payment was made in.
    description: :class:`str`
        What the payment was for.
    status: :class:`PaymentStatus`
        The status of the payment.
    created_at: :class:`datetime.datetime`
        The time the payment was made.
    sku: Optional[:class:`SKU`]
        The SKU the payment was for, if applicable.
    sku_id: Optional[:class:`int`]
        The ID of the SKU the payment was for, if applicable.
    sku_price: Optional[:class:`int`]
        The price of the SKU the payment was for, if applicable.
    subscription_plan_id: Optional[:class:`int`]
        The ID of the subscription plan the payment was for, if applicable.
    subscription: Optional[:class:`Subscription`]
        The subscription the payment was for, if applicable.
    payment_source: Optional[:class:`PaymentSource`]
        The payment source the payment was made with.
    payment_gateway: Optional[:class:`PaymentGateway`]
        The payment gateway the payment was made with, if applicable.
    payment_gateway_payment_id: Optional[:class:`str`]
        The ID of the payment on the payment gateway, if any.
    invoice_url: Optional[:class:`str`]
        The URL to download the VAT invoice for this payment, if available.
    refund_invoices_urls: List[:class:`str`]
        A list of URLs to download VAT credit notices for refunds on this payment, if available.
    refund_disqualification_reasons: List[:class:`RefundDisqualificationReason`]
        A list of reasons why the payment cannot be refunded, if any.
    error_code: Optional[:class:`int`]
        The JSON error code that occurred during the payment, if any.

        .. versionadded:: 2.1
    """

    __slots__ = (
        'id',
        'amount',
        'amount_refunded',
        'tax',
        'tax_inclusive',
        'currency',
        'description',
        'status',
        'created_at',
        'sku',
        'sku_id',
        'sku_price',
        'subscription_plan_id',
        'subscription',
        'payment_source',
        'payment_gateway',
        'payment_gateway_payment_id',
        'invoice_url',
        'refund_invoices_urls',
        'refund_disqualification_reasons',
        'error_code',
        '_refundable',
        '_flags',
        '_state',
    )

    def __init__(self, *, data: PaymentPayload, state: ConnectionState):
        self._state: ConnectionState = state
        self._update(data)

    def _update(self, data: PaymentPayload) -> None:
        state = self._state

        self.id: int = int(data['id'])
        self.amount: int = data['amount']
        self.amount_refunded: int = data.get('amount_refunded') or 0
        self.tax: int = data.get('tax') or 0
        self.tax_inclusive: bool = data.get('tax_inclusive', True)
        self.currency: str = data.get('currency', 'usd')
        self.description: str = data['description']
        self.status: PaymentStatus = try_enum(PaymentStatus, data['status'])
        self.created_at: datetime = parse_time(data['created_at'])
        self.sku: Optional[SKU] = SKU(data=data['sku'], state=state) if 'sku' in data else None
        self.sku_id: Optional[int] = _get_as_snowflake(data, 'sku_id')
        self.sku_price: Optional[int] = data.get('sku_price')
        self.subscription_plan_id: Optional[int] = _get_as_snowflake(data, 'sku_subscription_plan_id')
        self.payment_gateway: Optional[PaymentGateway] = (
            try_enum(PaymentGateway, data['payment_gateway']) if 'payment_gateway' in data else None
        )
        self.payment_gateway_payment_id: Optional[str] = data.get('payment_gateway_payment_id')
        self.invoice_url: Optional[str] = data.get('downloadable_invoice')
        self.refund_invoices_urls: List[str] = data.get('downloadable_refund_invoices', [])
        self.refund_disqualification_reasons: List[RefundDisqualificationReason] = [
            try_enum(RefundDisqualificationReason, r) for r in data.get('premium_refund_disqualification_reasons', [])
        ]
        self._refundable = data.get('premium_refund_disqualification_reasons') == []  # Hack for better DUX
        self._flags: int = data.get('flags', 0)

        # The subscription object does not include the payment source ID
        self.payment_source: Optional[PaymentSource] = (
            PaymentSource(data=data['payment_source'], state=state) if 'payment_source' in data else None
        )
        if 'subscription' in data and self.payment_source:
            data['subscription']['payment_source_id'] = self.payment_source.id  # type: ignore
        self.subscription: Optional[Subscription] = (
            Subscription(data=data['subscription'], state=state) if 'subscription' in data else None
        )

        metadata = data.get('metadata') or {}
        self.error_code: Optional[int] = metadata.get('billing_error_code')

    def __repr__(self) -> str:
        return f'<Payment id={self.id} amount={self.amount} currency={self.currency} status={self.status}>'

    def __str__(self) -> str:
        return self.description

    def is_subscription(self) -> bool:
        """:class:`bool`: Whether the payment was for a subscription."""
        return self.subscription is not None

    def is_premium_subscription(self) -> bool:
        """:class:`bool`: Whether the payment was for a Discord premium subscription."""
        return self.subscription is not None and self.subscription.type == SubscriptionType.premium

    def is_premium_subscription_gift(self) -> bool:
        """:class:`bool`: Whether the payment was for a Discord premium subscription gift."""
        return self.flags.gift and self.sku_id in self._state.premium_subscriptions_sku_ids.values()

    def is_purchased_externally(self) -> bool:
        """:class:`bool`: Whether the payment was made externally."""
        return self.payment_gateway in (PaymentGateway.apple, PaymentGateway.google)

    def is_refundable(self) -> bool:
        """:class:`bool`: Whether the payment is refundable.

        .. versionadded:: 2.1
        """
        return self.status == PaymentStatus.completed and self._refundable

    @property
    def flags(self) -> PaymentFlags:
        """:class:`PaymentFlags`: Returns the payment's flags."""
        return PaymentFlags._from_value(self._flags)

    async def void(self) -> None:
        """|coro|

        Void the payment. Only applicable for payments of status :attr:`PaymentStatus.pending`.

        Raises
        ------
        HTTPException
            Voiding the payment failed.
        """
        await self._state.http.void_payment(self.id)
        self.status = PaymentStatus.failed
