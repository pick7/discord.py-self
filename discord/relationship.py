"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

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

from typing import TYPE_CHECKING, Optional, Tuple, Union

from .enums import ConnectionType, FriendSuggestionReasonType, RelationshipAction, RelationshipType, Status, try_enum
from .mixins import Hashable
from .object import Object
from .utils import MISSING, parse_time

if TYPE_CHECKING:
    from datetime import datetime
    from typing_extensions import Self

    from .activity import ActivityTypes
    from .state import ConnectionState, Presence
    from .types.gateway import RelationshipEvent
    from .types.user import (
        FriendSuggestion as FriendSuggestionPayload,
        FriendSuggestionReason as FriendSuggestionReasonPayload,
        Relationship as RelationshipPayload,
    )
    from .user import User

__all__ = (
    'Relationship',
    'FriendSuggestionReason',
    'FriendSuggestion',
)


class Relationship(Hashable):
    """Represents a relationship in Discord.

    A relationship is like a friendship, a person who is blocked, etc.

    .. container:: operations

        .. describe:: x == y

            Checks if two relationships are equal.

        .. describe:: x != y

            Checks if two relationships are not equal.

        .. describe:: hash(x)

            Return the relationship's hash.

    Attributes
    -----------
    user: :class:`User`
        The user you have the relationship with.
    type: :class:`RelationshipType`
        The type of relationship you have.
    nick: Optional[:class:`str`]
        The user's friend nickname (if applicable).

        .. versionadded:: 1.9

        .. versionchanged:: 2.0
            Renamed ``nickname`` to :attr:`nick`.
    since: Optional[:class:`datetime.datetime`]
        When the relationship was created.
        Not available for all relationship types.

        .. versionadded:: 2.0
    """

    __slots__ = ('_presence', 'since', 'nick', 'type', 'user', '_state')

    if TYPE_CHECKING:
        user: User

    def __init__(self, *, state: ConnectionState, data: RelationshipPayload) -> None:
        self._state = state
        self._presence: Optional[Presence] = None
        self._update(data)

    def _update(self, data: Union[RelationshipPayload, RelationshipEvent]) -> None:
        self.type: RelationshipType = try_enum(RelationshipType, data['type'])
        self.nick: Optional[str] = data.get('nickname')
        self.since: Optional[datetime] = parse_time(data.get('since'))

        if not getattr(self, 'user', None):
            if 'user' in data:
                self.user = self._state.store_user(data['user'])  # type: ignore
            else:
                user_id = int(data['id'])
                self.user = self._state.get_user(user_id) or Object(id=user_id)  # type: ignore # Lying for better developer UX

    @classmethod
    def _from_implicit(cls, *, state: ConnectionState, user: User) -> Relationship:
        self = cls.__new__(cls)
        self._state = state
        self._presence = None
        self.type = RelationshipType.implicit
        self.nick = None
        self.since = None
        self.user = user
        return self

    @classmethod
    def _copy(cls, relationship: Self, presence: Presence) -> Self:
        self = cls.__new__(cls)  # to bypass __init__

        self._state = relationship._state
        self._presence = presence
        self.type = relationship.type
        self.nick = relationship.nick
        self.since = relationship.since
        self.user = relationship.user
        return self

    def __repr__(self) -> str:
        return f'<Relationship user={self.user!r} type={self.type!r} nick={self.nick!r}>'

    @property
    def id(self) -> int:
        """:class:`int`: Returns the relationship's ID."""
        return self.user.id

    @property
    def presence(self) -> Presence:
        state = self._state
        return self._presence or state._presences.get(self.user.id) or state.create_offline_presence()

    @property
    def status(self) -> Status:
        """:class:`Status`: The user's overall status.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return try_enum(Status, self.presence.client_status.status)

    @property
    def raw_status(self) -> str:
        """:class:`str`: The user's overall status as a string value.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return self.presence.client_status.status

    @property
    def mobile_status(self) -> Status:
        """:class:`Status`: The user's status on a mobile device, if applicable.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return try_enum(Status, self.presence.client_status.mobile or 'offline')

    @property
    def desktop_status(self) -> Status:
        """:class:`Status`: The user's status on the desktop client, if applicable.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return try_enum(Status, self.presence.client_status.desktop or 'offline')

    @property
    def web_status(self) -> Status:
        """:class:`Status`: The user's status on the web client, if applicable.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return try_enum(Status, self.presence.client_status.web or 'offline')

    @property
    def embedded_status(self) -> Status:
        """:class:`Status`: The user's status on an embedded client, if applicable.

        .. versionadded:: 2.1

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return try_enum(Status, self.presence.client_status.embedded or 'offline')

    def is_on_mobile(self) -> bool:
        """:class:`bool`: A helper function that determines if a user is active on a mobile device.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.
        """
        return self.presence.client_status.mobile is not None

    @property
    def activities(self) -> Tuple[ActivityTypes, ...]:
        """Tuple[Union[:class:`BaseActivity`, :class:`Spotify`]]: Returns the activities that
        the user is currently doing.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.

        .. note::

            Due to a Discord API limitation, a user's Spotify activity may not appear
            if they are listening to a song with a title longer
            than 128 characters. See :issue:`1738` for more information.
        """
        return self.presence.activities

    @property
    def activity(self) -> Optional[ActivityTypes]:
        """Optional[Union[:class:`BaseActivity`, :class:`Spotify`]]: Returns the primary
        activity the user is currently doing. Could be ``None`` if no activity is being done.

        .. versionadded:: 2.0

        .. note::

            This is only provided for type :class:`RelationshipType.friend` and :class:`RelationshipType.implicit` relationships.

        .. note::

            Due to a Discord API limitation, this may be ``None`` if
            the user is listening to a song on Spotify with a title longer
            than 128 characters. See :issue:`1738` for more information.

        .. note::

            A user may have multiple activities, these can be accessed under :attr:`activities`.
        """
        if self.activities:
            return self.activities[0]

    async def delete(self) -> None:
        """|coro|

        Deletes the relationship.

        Depending on the type, this could mean unfriending or unblocking the user,
        denying an incoming friend request, discarding an outgoing friend request, etc.

        Raises
        ------
        HTTPException
            Deleting the relationship failed.
        """
        action = RelationshipAction.deny_request
        if self.type is RelationshipType.friend:
            action = RelationshipAction.unfriend
        elif self.type is RelationshipType.blocked:
            action = RelationshipAction.unblock
        elif self.type is RelationshipType.incoming_request:
            action = RelationshipAction.deny_request
        elif self.type is RelationshipType.outgoing_request:
            action = RelationshipAction.remove_pending_request

        await self._state.http.remove_relationship(self.user.id, action=action)

    async def accept(self) -> None:
        """|coro|

        Accepts the relationship request. Only applicable for
        type :class:`RelationshipType.incoming_request`.

        Raises
        -------
        HTTPException
            Accepting the relationship failed.
        """
        await self._state.http.add_relationship(self.user.id, action=RelationshipAction.accept_request)

    async def edit(self, nick: Optional[str] = MISSING) -> None:
        """|coro|

        Edits the relationship.

        .. versionadded:: 1.9

        .. versionchanged:: 2.0
            Changed the name of the method to :meth:`edit`.
            The edit is no longer in-place.

        Parameters
        ----------
        nick: Optional[:class:`str`]
            The nickname to change to. Can be ``None`` to denote no nickname.

        Raises
        -------
        HTTPException
            Changing the nickname failed.
        """
        payload = {}
        if nick is not MISSING:
            payload['nickname'] = nick

        await self._state.http.edit_relationship(self.user.id, **payload)


class FriendSuggestionReason:
    """Represents a reason why a user was suggested as a friend to you.

    .. versionadded:: 2.1

    Attributes
    -----------
    type: :class:`FriendSuggestionReasonType`
        The type of friend suggestion reason.
    platform: :class:`ConnectionType`
        The platform the user was suggested from.
    name: :class:`str`
        The user's name on the platform.
    """

    __slots__ = ('type', 'platform', 'name')

    def __init__(self, data: FriendSuggestionReasonPayload):
        # This entire model is mostly unused by any client, so I can't be sure on types
        # Also because of this, I'm treating everything as optional just in case
        self.type: FriendSuggestionReasonType = try_enum(FriendSuggestionReasonType, data.get('type', 0))
        self.platform: ConnectionType = try_enum(ConnectionType, data.get('platform'))
        self.name: str = data.get('name') or ''

    def __repr__(self) -> str:
        return f'<FriendSuggestionReason platform={self.platform!r} name={self.name!r}>'


class FriendSuggestion(Hashable):
    """Represents a friend suggestion on Discord.

    .. container:: operations

        .. describe:: x == y

            Checks if two friend suggestions are equal.

        .. describe:: x != y

            Checks if two friend suggestions are not equal.

        .. describe:: hash(x)

            Return the suggestion's hash.

    .. versionadded:: 2.1

    Attributes
    -----------
    user: :class:`User`
        The suggested user.
    reasons: List[:class:`FriendSuggestionReason`]
        The reasons why the user was suggested.
    from_user_contacts: :class:`bool`
        Whether the suggested user had the current user in their contacts.
    """

    __slots__ = ('user', 'reasons', 'from_user_contacts', '_state')

    def __init__(self, *, state: ConnectionState, data: FriendSuggestionPayload):
        self._state = state
        self.user = state.store_user(data['suggested_user'])
        self.reasons = [FriendSuggestionReason(r) for r in data.get('reasons', [])]
        self.from_user_contacts: bool = data.get('from_suggested_user_contacts', False)

    def __repr__(self) -> str:
        return (
            f'<FriendSuggestion user={self.user!r} reasons={self.reasons!r} from_user_contacts={self.from_user_contacts!r}>'
        )

    async def accept(self) -> None:
        """|coro|

        Accepts the friend suggestion.
        This creates a :class:`Relationship` of type :class:`RelationshipType.outgoing_request`.

        Raises
        -------
        HTTPException
            Accepting the relationship failed.
        """
        await self._state.http.add_relationship(self.user.id, action=RelationshipAction.friend_suggestion)

    async def delete(self) -> None:
        """|coro|

        Ignores the friend suggestion.

        Raises
        ------
        HTTPException
            Deleting the relationship failed.
        """
        await self._state.http.delete_friend_suggestion(self.user.id)
