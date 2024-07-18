# Planning for separate services

We're going to want to try and reduce coupling as much as possible so that we can eventually break this all up into microservices down the road.

## Astrology
- Personal info (signs/ascendants)
- Comparison between two people

## Authentication / Users
- Authenticate Users
- Refresh token
- Create User
- Update User
- Delete User
- Deactivate User
- Profile
    - Stats
    - Follow
    - Unfollow
    - Follow Request
    - Request to Follow
    - Mute Accounts
    - Mute Words/Phrases
    - Block Accounts (Remember to integrate this into dating feed)
    - Block Words/Phrases
    - Profile Visits (track, but not necessarily show/notify)
    - Grouping of posts (like you can create a group for your favorite posts, posts with photos of you, etc)
    - Meme Collection

## Chat
- One on One Direct Message
- Group Direct Message
- One on One Dating Message
- Group Dating Message
- WebSocket
- Read receipts
- Read At
- Attachments
    - Posts
    - Links to profiles
    - Links to posts
    - Links to websites
    - Pictures
    - GIFs
    - Videos

## Dating
- Matches
- Swiping
- Potential Matches
- Swiping on actual accounts
- Premium ability to view who has swiped on your profile
- Ability to view historical swipes and change them
- Reset your historical swipes
- Can compare your results and compatibility and suggestions with someone you're dating without having to activate the dating side of things

## Discussions / Roadmap / Ideas / Rants
- Post roadmaps
- People can vote on a other people's ideas
- The more the votes, the higher the priority
- Mark ideas as green when they've been implemented and add to user's stats
- Semantic Search to make sure there aren't any similar ones

## Groups
- Should feel like Reddit and the Reddit feed
- Subscribe to groups like you can subscribe to subreddits
- NSFW Groups
- Can mix in with your general feed
- Create Groups
- Groups can have admins

## Events/Pages
- Create Events
- Admins
- Date
- Private/Public
- Location

## Meme Collection / Studio
- Be able to tag a meme as a specific meme instance
- Can view other memes related to that
- Can make stickers public
- Create Memes in the Studio

## Mood Board
- Pinterest style
- Tag links to purchase articles of clothing

## Notifications
- Push tokens
- WebSocket

## Personality
- Personal info (signs/ascendants)
- Comparison between two people

## Posts
- General Posts
- Video Posts
- Reposts
- Quote Reposts
- Replies to posts
- Replies to replies
- Attachments
    - Photos
    - Videos
    - Links to websites
    - Links to other posts
- Hashtags
- Tagging of other users
- Daily leaderboards
- Woos/Boos
- Impressions
- Blog Posts

## Psychic / Prediction
- People can create predictions and have voting options
- Accuracy ratio

## Recommendation Engine
- Azure Cosmos DB for Apache Gremlin
- Useful traits for recommendations:
    - Location
    - Following
    - Followers
    - Liked Posts
    - Reposts
    - Quote Reposts
    - Dislikes
    - Swipes
    - Messaged With
    - Groups Involved In
    - Predictions
    - Profile Visits

## Search
- Semantic Search
- Advanced Filtering
    - Created date
    - Contains these words
    - Contains some of these words
    - Only people you're following
    - Sort by popularity
    - Sort by latest
    - Show specific types
        - Posts
        - Videos
        - Images
        - Users
        - Predictions
            - All
            - Ongoing
        - Roadmap
    - Filter nearby
    - Events
- User Search History

## Stats
- Profile Visits
- Total Likes
- Total Reposts
- Total Quote Reposts
- Average Likes
- How many times you've made it to the leaderboard
- Correct prediction votes



# Routes

## Dating

- dating-swipe
    - receiver_id: OID
    - sender_id: OID
    - positive: Boolean

- dating-profile-update
    - user_id: OID
    - field: String
    - value: Any

- match-triggered
    - user_one: OID
    - user_two: OID

## Personality

- question-answered
    - user_id: OID
    - question_id: OID
    - postive: Boolean


## Astrology

- astrology-information-updated
    - user_id: OID
    - longitude: float
    - latitude: float
    - birth: datetime

- house-system-update
    - user_id: OID
    - house_system: String

## Posts

- post-liked
    - post_type: IntEnum
    - post_id: OID
    - post_author: OID
    - liked_by: OID

- post-seen
    - post_type: IntEnum
    - post_id: OID
    - post_author: OID
    - viewed_by: OID

- post-reposted
    - post_type: IntEnum
    - post_id: OID
    - post_author: OID
    - reposted_by: OID

## Messaging/Chat

- message-sent
    - chat_type: ChatType
    - chat_id: OID
    - user_id: OID
    - has_media_attachment: Boolean
    - media_attachment_type: MediaType
    - media_source: String

- message-read
    - chat_type: ChatType
    - chat_id: OID
    - user_id: OID
    - read_at: Datetime

- user-started-typing-chat
    - chat_type: ChatType
    - chat_id: OID
    - user_id: OID

- user-stopped-typing-chat
    - chat_type: ChatType
    - chat_id: OID
    - user_id: OID



## Search

- search-created
    - user_id: OID
    - search_text: String
    - search_image: String
    - filters: Filters

## Discussions

- idea-created
    - user_id: OID
    - data: DiscussionData

- idea-completed
    - idea_id: OID

## Groups

- group-created
    - group_id: OID
    - group_name: String
    - created_by: OID

- group-admin-created
    - group_id: OID
    - user_id: OID

- group-post-created
    - group_id: OID
    - user_id: OID

## Predictions / Psychic

- prediction-created
    - prediction_id: OID

- prediction-ended
    - prediction_id: OID

- user-prediction:
    - prediction_id: OID
    - user_prediction_id: OID
    - prediction_made: Any


# Neo4J / Graphs

## Nodes
- User
- Posts
- Predictions
- Questions

## Relationships
- User saved meme
- User owns meme
- User likes post
- User dislikes post
- User created post
- User reposted post
- User viewed post
- User quoted post
- User replied to post
- User swiped left/right on user
- User messaged user
- User followed user
- User predicted prediction
- User created prediction
- User answered question
- User matched with user
- User blocked user
- User muted user
- User muted phrase
- User searched
- Leaderboard has posts
- User has sign ___ for ___
- User is in group
- User is admin of group
- User is admin of chat
- User created chat
- User is in chat
- Message in chat
- User reacted to message
- User shared post with User
- User from metropolitan
- User is ___ political party
- User has ___ trait
- User has notification
- User read notification
- User has not read notification