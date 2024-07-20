from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, EmailStr

from app.posts.schemas import PostResponse
from app.shared.settings import settings_model


class AppleTokenResponse(BaseModel):
    """Represents the response structure for an Apple token request.

    Attributes:
        access_token (str): The access token issued by Apple.
        token_type (str): The type of token, typically "Bearer".
        expires_in (str): The expiration time of the access token in seconds.
        refresh_token (str): The refresh token used to obtain a new access token.
        id_token (str): The ID token containing user information.
    """

    access_token: str
    token_type: str
    expires_in: str
    refresh_token: str
    id_token: str


class AppleTokenRequest(BaseModel):
    """Represents the request structure for an Apple token request.

    Attributes:
        client_id (str): The client ID for the Apple app.
        client_secret (str): The client secret for the Apple app.
        code (str): The authorization code received from Apple.
        grant_type (str): The type of grant, default is "authorization_code".
    """

    client_id: str = str(settings_model.apple.client_id)
    client_secret: str = str(settings_model.apple.client_secret)
    code: str
    grant_type: str = "authorization_code"



class RefreshTokenRequest(BaseModel):
    """Request model for refreshing a user's access token."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for a user's access token."""

    access_token: str
    refresh_token: str
    token_id: str

class VerifiedUser(BaseModel):
    """Represents a verified user."""

    user_id: str
    apple_id: str

class Religion(IntEnum):
    """Represents a user's religion."""

    ATHEISM = 0
    AGNOSTICISM = 1
    CHRISTIANITY = 2
    ISLAM = 3
    JUDAISM = 4
    HINDUISM = 5
    BUDDHISM = 6
    SIKHISM = 7
    TAOISM = 8
    SHINTO = 9
    PAGANISM = 10
    SPIRITUAL_BUT_NOT_RELIGIOUS = 11
    OTHER = 12
    PREFER_NOT_TO_SAY = 13


class Gender(IntEnum):
    """Represents a user's gender."""

    MALE = 0
    FEMALE = 1
    NON_BINARY = 2
    GENDERQUEER = 3
    GENDERFLUID = 4
    AGENDER = 5
    BIGENDER = 6
    TWO_SPIRIT = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class SexualOrientation(IntEnum):
    """Represents a user's sexual orientation."""

    HETEROSEXUAL = 0
    HOMOSEXUAL = 1
    BISEXUAL = 2
    PANSEXUAL = 3
    ASEXUAL = 4
    QUEER = 6
    QUESTIONING = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class RelationshipStatus(IntEnum):
    """Represents a user's relationship status."""

    SINGLE = 0
    IN_A_RELATIONSHIP = 1
    ENGAGED = 2
    MARRIED = 3
    DIVORCED = 4
    WIDOWED = 5
    COMPLICATED = 6
    OPEN_RELATIONSHIP = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class EducationLevel(IntEnum):
    """Represents a user's education level."""

    HIGH_SCHOOL = 0
    SOME_COLLEGE = 1
    ASSOCIATES_DEGREE = 2
    BACHELORS_DEGREE = 3
    MASTERS_DEGREE = 4
    DOCTORATE = 5
    TRADE_SCHOOL = 6
    OTHER = 7
    PREFER_NOT_TO_SAY = 8


class LookingFor(IntEnum):
    """Represents a user's looking for."""

    FRIENDS = 0
    CASUAL_DATING = 1
    LONG_TERM_RELATIONSHIP = 2
    MARRIAGE = 3
    HOOKUP = 4
    FLING = 5
    SITUATIONSHIP = 6
    NEED_A_DATE_TO_EVENT = 7
    NETWORKING = 8
    ACTIVITY_PARTNERS = 9
    CHAT_BUDDIES = 10
    NOT_SURE = 11
    OTHER = 12
    PREFER_NOT_TO_SAY = 13


class School(BaseModel):
    """Represents a user's school."""

    name: str
    start_year: int
    end_year: int | None = None
    degree: str | None = None
    major: str | None = None


class Education(BaseModel):
    """Represents a user's education."""

    highest_level: EducationLevel
    schools: list[School] = []


class HasChildren(IntEnum):
    """Represents a user's children status."""

    NO = 0
    YES = 1
    PREFER_NO_TO_SAY = 2


class WantsChildren(IntEnum):
    """Represents a user's wants children status."""

    NEVER = 0
    SOMEDAY = 1
    YES = 2
    NOT_SURE = 3
    PREFER_NOT_TO_SAY = 4


class BasicUserResponse(BaseModel):
    """Response model for getting a basic user."""

    user_id: str
    apple_id: str
    email: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool | None = True
    account_private: bool | None = False
    username: str | None = None
    refresh_token: str | None = None
    following_count: int | None = 0
    followers_count: int | None = 0
    created_at: datetime | None = None
    last_login: datetime | None = None
    last_seen: datetime | None = None


class User(BaseModel):
    """Represents a basic user."""

    # Basic user information
    user_id: str
    apple_id: str
    email: str

    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool = True
    account_private: bool = False
    username: str | None = None
    refresh_token: str | None = None
    following_count: int = 0
    followers_count: int = 0
    profile_location: tuple[float, float] | None = None
    created_at: datetime | None = None
    last_login: datetime | None = None
    last_seen: datetime | None = None

    # User traits
    introversion_extraversion: float | None = None
    thinking_feeling: float | None = None
    sensing_intuition: float | None = None
    judging_perceptive: float | None = None
    conscientiousness: float | None = None
    agreeableness: float | None = None
    neuroticism: float | None = None
    individualism_collectivism: float | None = None
    libertarianism_authoritarianism: float | None = None
    environmentalism_anthropocentrism: float | None = None
    isolationism_interventionism: float | None = None
    security_freedom: float | None = None
    noninterventionism_interventionism: float | None = None
    equity_meritocracy: float | None = None
    empathy: float | None = None
    honesty: float | None = None
    humility: float | None = None
    independence: float | None = None
    patience: float | None = None
    persistence: float | None = None
    playfulness: float | None = None
    rationality: float | None = None
    religiosity: float | None = None
    self_acceptance: float | None = None
    sex_focus: float | None = None
    thriftiness: float | None = None
    thrill_seeking: float | None = None
    drug_friendliness: float | None = None
    emotional_openness_in_relationships: float | None = None
    equanimity: float | None = None
    family_focus: float | None = None
    loyalty: float | None = None
    preference_for_monogamy: float | None = None
    trust: float | None = None
    self_esteem: float | None = None
    anxious_attachment: float | None = None
    avoidant_attachment: float | None = None
    career_focus: float | None = None
    emphasis_on_boundaries: float | None = None
    fitness_focus: float | None = None
    stability_of_self_image: float | None = None
    love_focus: float | None = None
    maturity: float | None = None
    wholesomeness: float | None = None
    traditionalist_view_of_love: float | None = None
    openness_to_experience: float | None = None

    # User astrology
    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None
    sun: str | None = None
    moon: str | None = None
    ascendant: str | None = None
    mercury: str | None = None
    venus: str | None = None
    mars: str | None = None
    jupiter: str | None = None
    saturn: str | None = None
    uranus: str | None = None
    neptune: str | None = None
    pluto: str | None = None

    # User dating profile options
    dating_active: bool
    recent_location: tuple[float, float]
    dating_photos: list[str] = []
    dating_bio: str = ""

    height: int | None = None
    gender: Gender
    sexual_orientation: SexualOrientation
    relationship_status: RelationshipStatus
    religion: Religion
    education: Education
    highest_education_level: EducationLevel
    looking_for: list[LookingFor]
    has_children: HasChildren
    wants_children: WantsChildren
    has_tattoos: bool

    # User dating profile flags
    show_gender: bool = True
    show_sexual_orientation: bool = True
    show_relationship_status: bool = True
    show_religion: bool = True
    show_education: bool = True
    show_looking_for: bool = True
    show_schools: bool = True
    show_has_children: bool = True
    show_wants_children: bool = True

    # User dating profile preferences
    max_distance: float = 10000
    minimum_age: int = 0
    maximum_age: int = 110
    minimum_height: int = 0
    maximum_height: int = 108
    gender_preferences: list[Gender] = []
    has_children_preferences: list[HasChildren] = []
    wants_children_preferences: list[WantsChildren] = []
    education_level_preferences: list[EducationLevel] = []
    religion_preferences: list[Religion] = []
    sexual_orientation_preferences: list[SexualOrientation] = []
    relationship_status_preferences: list[RelationshipStatus] = []
    looking_for_preferences: list[LookingFor] = []

    # Notifications Bells
    last_checked_boops: datetime | None = None
    last_checked_messages: datetime | None = None
    last_checked_notifications: datetime | None = None
    last_checked_dating: datetime | None = None
    last_checked_predictions: datetime | None = None
    last_checked_follow_requests: datetime | None = None

    # Stats
    swiped_left_count: int = 0 # How many times the user has been swiped left on
    swiped_right_count: int = 0 # How many times the user has been swiped right on
    likes_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    replies_count: int = 0
    bookmarked_count: int = 0
    correct_prediction_count: int = 0
    predictions_made_count: int = 0
    profile_visits_count: int = 0



class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    # We need to leave all fields as None to avoid overwriting existing values

    # Allowed fields to update: basic user information
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool | None = None
    account_private: bool | None = None
    username: str | None = None
    profile_location: tuple[float, float] | None = None
    profile_bio: str | None = None

    # Allowed fields to update: astrology
    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None

    # Allowed fields to update: dating profile
    dating_active: bool | None = None
    recent_location: tuple[float, float] | None = None
    dating_photos: list[str] | None = None
    dating_bio: str | None = None

    height: int | None = None
    gender: Gender | None = None
    sexual_orientation: SexualOrientation | None = None
    relationship_status: RelationshipStatus | None = None
    religion: Religion | None = None
    education: Education | None = None
    highest_education_level: EducationLevel | None = None
    looking_for: list[LookingFor] | None = None
    has_children: HasChildren | None = None
    wants_children: WantsChildren | None = None
    has_tattoos: bool | None = None

    # Allowed fields to update: dating profile preferences
    max_distance: float | None = None
    minimum_age: int | None = None
    maximum_age: int | None = None
    minimum_height: int | None = None
    maximum_height: int | None = None
    gender_preferences: list[Gender] | None = None
    has_children_preferences: list[HasChildren] | None = None
    wants_children_preferences: list[WantsChildren] | None = None
    education_level_preferences: list[EducationLevel] | None = None
    religion_preferences: list[Religion] | None = None
    sexual_orientation_preferences: list[SexualOrientation] | None = None
    relationship_status_preferences: list[RelationshipStatus] | None = None
    looking_for_preferences: list[LookingFor] | None = None

class DetailedDatingProfileResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    account_private: bool
    username: str
    distance: float | None = None
    dating_photos: list[str] | None = None
    dating_bio: str | None = None
    height: int | None = None
    gender: Gender | None = None
    sexual_orientation: SexualOrientation | None = None
    relationship_status: RelationshipStatus | None = None
    religion: Religion | None = None
    # education: Education | None = None
    highest_education_level: EducationLevel | None = None
    looking_for: list[LookingFor] | None = None
    has_children: HasChildren | None = None
    wants_children: WantsChildren | None = None
    has_tattoos: bool | None = None


class UserProfileResponse(BaseModel):
    """Response model for getting a user's profile."""

    user: BasicUserResponse
    posts: list[PostResponse]
    follows_user: bool
    has_swiped_right: bool
    has_swiped_left: bool
    has_more: bool
    next_cursor: datetime | None = None
    is_private: bool = False

class CreateUserResponse(BaseModel):
    """Response model for creating a new user."""

    user_id: str
    apple_id: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    display_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    created_at: datetime
    last_login: datetime


class SimpleUserResponse(BaseModel):
    """Response model for a single blocked user."""

    user_id: str
    profile_photo: str | None = None
    username: str | None = None
    display_name: str | None = None
    created_at: datetime

class UsernameCheckResponse(BaseModel):
    """Response model for checking username availability."""

    username_exists: bool


class FollowingResponse(BaseModel):
    """Response model for getting a list of followed users."""

    user_follows: list[SimpleUserResponse]
    has_more: bool
    next_cursor: datetime | None = None


class FollowRequestResponse(BaseModel):
    """Response model for getting a list of follow requests."""

    user_follow_requests: list[SimpleUserResponse]


class SendFollowReqRequest(BaseModel):
    """Request model for sending a follow request."""

    user_id: str

class GetFollowersResponse(BaseModel):
    """Response model for getting a list of followers."""

    followers: list[SimpleUserResponse]
    has_more: bool
    last_follow_datetime: datetime | None = None


class GetFollowRecommendationsResponse(BaseModel):
    """Response model for getting a list of users that the user may want to follow."""

    recommendations: list[SimpleUserResponse]


"""---------------- USER BLOCKS -----------------"""
class BlockedUsersResponse(BaseModel):
    """Response model for getting a list of blocked users."""

    blocked_list: list[SimpleUserResponse]


class BlockUserRequest(BaseModel):
    """Request model for blocking a user."""

    user_id: str


"""---------------- USER MUTES -----------------"""
class MutedUsersResponse(BaseModel):
    """Response model for getting a list of muted users."""

    muted_list: list[SimpleUserResponse]

class MuteUserRequest(BaseModel):
    """Request model for muting a user."""

    user_id: str