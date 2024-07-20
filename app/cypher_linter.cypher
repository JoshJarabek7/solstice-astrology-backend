    MATCH (user:User {user_id: $user_id})
    MATCH (bookmark_group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    MATCH (post:Post {post_id: $post_id})
    MATCH (author:User)-[:POSTED]->(post)

    // Check for blocks
    OPTIONAL MATCH (user)-[:BLOCKS]-(author)
    WITH user, bookmark_group, post, author, COUNT(DISTINCT author) AS block_count
    WHERE block_count = 0

    // Check for privacy
    OPTIONAL MATCH (user)-[:FOLLOWS]->(author)
    WITH user, bookmark_group, post, author, block_count, COUNT(DISTINCT author) AS follows_count
    WHERE block_count = 0 AND (NOT author.account_private OR follows_count > 0)

    // Create the bookmark
    CREATE (bookmark:Bookmark {bookmark_id: $bookmark_id, created_at: $created_at})
    MERGE (user)-[:BOOKMARKED]->(bookmark)
    MERGE (bookmark)-[:BOOKMARKS]->(post)
    MERGE (bookmark_group)-[:CONTAINS]->(bookmark)
    SET bookmark_group.bookmark_count = COALESCE(bookmark_group.bookmark_count, 0) + 1
    SET author.bookmarked_count = COALESCE(author.bookmarked_count, 0) + 1
    RETURN bookmark