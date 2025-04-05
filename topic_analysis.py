import re
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer

def analyze_trending_topics(tweets):
    """Analyze tweets to extract trending topics with emphasis on engagement metrics"""
    
    # Extract all hashtags and weighted by engagement
    all_hashtags = []
    tweet_texts = []
    high_engagement_tweets = []
    top_conversations = {}
    
    for tweet in tweets.data:
        tweet_texts.append(tweet.text)
        
        # Calculate engagement score (likes + retweets*2 + replies*1.5)
        engagement_score = 0
        if hasattr(tweet, 'public_metrics'):
            metrics = tweet.public_metrics
            like_count = metrics.get('like_count', 0)
            retweet_count = metrics.get('retweet_count', 0)
            reply_count = metrics.get('reply_count', 0)
            quote_count = metrics.get('quote_count', 0)
            
            engagement_score = like_count + (retweet_count*2) + (reply_count*1.5) + (quote_count*1.8)
        
        # Store high engagement tweets for later analysis
        if engagement_score > 10:  # Threshold for "high engagement"
            high_engagement_tweets.append({
                'text': tweet.text,
                'engagement': engagement_score,
                'id': tweet.id
            })
        
        # Track conversation threads
        if hasattr(tweet, 'conversation_id') and tweet.conversation_id:
            convo_id = tweet.conversation_id
            if convo_id in top_conversations:
                top_conversations[convo_id]['count'] += 1
                top_conversations[convo_id]['engagement'] += engagement_score
            else:
                top_conversations[convo_id] = {
                    'count': 1, 
                    'engagement': engagement_score,
                    'sample_text': tweet.text[:100]
                }
        
        # Weight hashtags by engagement
        if hasattr(tweet, 'entities') and tweet.entities and 'hashtags' in tweet.entities:
            hashtags = [tag['tag'].lower() for tag in tweet.entities['hashtags']]
            
            # Apply engagement weighting - more engaged tweets' hashtags count more
            weight = max(1, engagement_score/10)
            weighted_hashtags = hashtags * int(weight)
            all_hashtags.extend(weighted_hashtags)
    
    # Count hashtag occurrences with engagement weighting applied
    hashtag_counts = Counter(all_hashtags)
    top_hashtags = hashtag_counts.most_common(10)
    
    # Extract key phrases using scikit-learn (free)
    vectorizer = CountVectorizer(
        ngram_range=(2, 3),  # Look for 2-3 word phrases
        stop_words='english',
        min_df=2  # At least 2 occurrences
    )
    
    # Clean tweets for phrase analysis
    cleaned_texts = []
    for text in tweet_texts:
        # Remove URLs, mentions, hashtags
        clean_text = re.sub(r'http\S+|@\S+|#\S+', '', text)
        # Remove special characters
        clean_text = re.sub(r'[^\w\s]', '', clean_text)
        cleaned_texts.append(clean_text)
    
    # Only proceed if we have enough data
    if len(cleaned_texts) < 2:
        return {"hashtags": top_hashtags, "phrases": []}
    
    # Extract phrases
    try:
        X = vectorizer.fit_transform(cleaned_texts)
        
        # Get all features (phrases)
        all_features = vectorizer.get_feature_names_out()
        
        # Sum up occurrences of each phrase
        phrase_counts = X.sum(axis=0).A1
        
        # Create list of (phrase, count) tuples
        phrases = [(all_features[i], phrase_counts[i]) for i in range(len(all_features))]
        
        # Sort by count in descending order
        top_phrases = sorted(phrases, key=lambda x: x[1], reverse=True)[:10]
        
    except Exception as e:
        print(f"Warning: Phrase extraction error: {e}")
        top_phrases = []
    
    return {
        "hashtags": top_hashtags, 
        "phrases": top_phrases
    }

def create_summary(analysis_results, tweet_count):
    """Generate a readable summary from the analysis results"""
    
    from datetime import datetime
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    summary = f"📊 Daily Community Trends: {current_date} 📊\n\n"
    
    # Add trending hashtags
    if analysis_results["hashtags"]:
        summary += "🔥 Top Hashtags:\n"
        for i, (hashtag, count) in enumerate(analysis_results["hashtags"][:5], 1):
            summary += f"{i}. #{hashtag} ({count} mentions)\n"
        summary += "\n"
    
    # Add trending phrases
    if analysis_results["phrases"]:
        summary += "💬 Trending Topics:\n"
        for i, (phrase, count) in enumerate(analysis_results["phrases"][:5], 1):
            summary += f"{i}. {phrase} ({count} mentions)\n"
        summary += "\n"
    
    # Add simple stats
    summary += f"Today's activity: {tweet_count} tweets analyzed"
    
    return summary
