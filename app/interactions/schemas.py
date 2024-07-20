from pydantic import BaseModel

"""---------------- VIEWS -----------------"""
class ViewedProfileRequest(BaseModel):
    viewed_user_id: str

class ViewedProfileEvent(ViewedProfileRequest):
    viewing_user_id: str

class ViewedPostRequest(BaseModel):
    viewed_post_id: str

class ViewedPostEvent(ViewedPostRequest):
    viewing_user_id: str

"""---------------- LIKES -----------------"""
class LikedPostRequest(BaseModel):
    post_id: str

class LikedPostEvent(LikedPostRequest):
    user_id: str

class UnlikedPostRequest(BaseModel):
    post_id: str

class UnlikedPostEvent(UnlikedPostRequest):
    user_id: str

"""---------------- REPOSTS -----------------"""
class RepostedPostRequest(BaseModel):
    post_id: str

class RepostedPostEvent(RepostedPostRequest):
    user_id: str

class UnrepostedPostRequest(BaseModel):
    post_id: str

class UnrepostedPostEvent(UnrepostedPostRequest):
    user_id: str

"""---------------- BOOKMARKS -----------------"""
class AddBookmarkRequest(BaseModel):
    bookmark_group_id: str
    post_id: str

class AddBookmarkEvent(AddBookmarkRequest):
    user_id: str

class DeleteBookmarkRequest(BaseModel):
    bookmark_id: str

class DeleteBookmarkEvent(DeleteBookmarkRequest):
    user_id: str


"""---------------- SWIPES -----------------"""
class SwipeRightEvent(BaseModel):
    target_user_id: str
    requesting_user_id: str

class MatchEvent(BaseModel):
    user_one: str
    user_two: str
