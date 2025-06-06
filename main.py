# main.py - Your main bot script

import tweepy
import os
import json
import time
from datetime import datetime
from topic_analysis import analyze_trending_topics, create_summary

def run_twitter_bot():
    """Main function to run the Twitter bot"""
    
    # Load environment variables (set in GitHub secrets)
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    consumer_key = os.environ.get("TWITTER_API_KEY")
    consumer_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    
    # Configure read-only client (for collecting data)
    read_client = tweepy.Client(
        bearer_token=bearer_token
    )
    
    # Configure read-write client (for posting)
    write_client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # 1. Collect Data with rate limit handling
    print("Collecting community tweets...")
    
    # Define Nigerian UK community ID
    community_id = "1503991265226022912"
    
    # For Basic tier API, focus on general Nigerian UK conversations
    search_query = "(Nigerian UK OR Nigerians in UK OR Nigerian London OR Naija UK OR UK Naija OR Nigerian Britain) -is:retweet"
    
    # Add rate limit handling
    tweet_data = None
    max_retries = 3
    retry_count = 0
    retry_delay = 15  # seconds
    
    while retry_count < max_retries and tweet_data is None:
        try:
            # Reduce max_results to be gentler on rate limits
            tweets = read_client.search_recent_tweets(
                query=search_query,
                max_results=10,  # Reduced from 100 to avoid rate limits
                tweet_fields=["created_at", "public_metrics", "entities", "author_id", "conversation_id"],
                sort_order="relevancy"  # This prioritizes tweets with higher engagement
            )
            tweet_data = tweets
            break
        except tweepy.errors.TooManyRequests as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"Rate limit exceeded. Waiting {retry_delay} seconds before retry {retry_count}/{max_retries}...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("Maximum retries reached. Using empty data set.")
                # Create empty placeholder for processing to continue
                from collections import namedtuple
                EmptyData = namedtuple('EmptyData', ['data'])
                tweet_data = EmptyData(data=[])
        except Exception as e:
            print(f"Error collecting tweets: {e}")
            # Create empty placeholder for processing to continue
            from collections import namedtuple
            EmptyData = namedtuple('EmptyData', ['data'])
            tweet_data = EmptyData(data=[])
            break
    
    # Use the collected tweets (or empty data if failed)
    tweets = tweet_data
    
    if not hasattr(tweets, 'data') or not tweets.data:
        print("No tweets found. Creating minimal summary.")
        tweet_count = 0
        # Create a fallback message instead of exiting
        fallback_message = "Today's Nigerian UK community update: Not enough data available today. Will try again tomorrow!"
        try:
            print("Posting fallback message...")
            write_client.create_tweet(text=fallback_message)
            print("Posted fallback message successfully")
        except Exception as e:
            print(f"Error posting fallback message: {e}")
        return
    
    tweet_count = len(tweets.data)
    print(f"Collected {tweet_count} tweets")
    
    # 2. Analyze Topics
    print("Analyzing trending topics with engagement metrics...")
    analysis_results = analyze_trending_topics(tweets)
    
    # Add high engagement tweets to results
    high_engagement_tweets = []
    top_conversations = {}
    
    # Process tweets by engagement level
    for tweet in tweets.data:
        # Calculate engagement score
        engagement_score = 0
        if hasattr(tweet, 'public_metrics'):
            metrics = tweet.public_metrics
            engagement_score = (
                metrics.get('like_count', 0) + 
                metrics.get('retweet_count', 0) * 2 + 
                metrics.get('reply_count', 0) * 1.5 +
                metrics.get('quote_count', 0) * 1.8
            )
        
        # Store high engagement tweets
        if engagement_score > 10:
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
    
    # Sort high engagement tweets and conversations
    high_engagement_tweets.sort(key=lambda x: x['engagement'], reverse=True)
    top_conversations = sorted(
        top_conversations.items(),
        key=lambda x: (x[1]['count'], x[1]['engagement']),
        reverse=True
    )[:5]
    
    # Add to analysis results
    analysis_results['high_engagement'] = high_engagement_tweets[:3]  # Top 3 only
    analysis_results['top_conversations'] = top_conversations
    
    # 3. Create Enhanced Summary
    print("Creating engagement-focused summary...")
    summary = create_summary(analysis_results, tweet_count)
    print("\nSummary Preview:")
    print("-------------------")
    print(summary)
    print("-------------------")
    
    # 4. Post to Twitter
    try:
        print("Posting to Twitter...")
        response = write_client.create_tweet(text=summary)
        print(f"Successfully posted tweet! ID: {response.data['id']}")
    except Exception as e:
        print(f"Error posting to Twitter: {e}")
    
    # 5. Save results to GitHub repo for historical tracking
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Save daily results
        with open(f"results/daily_{today}.json", "w") as f:
            # Don't save full tweet data to avoid storage limits
            json.dump({
                "date": today,
                "tweet_count": tweet_count,
                "top_hashtags": analysis_results["hashtags"],
                "top_phrases": analysis_results["phrases"],
                "summary": summary
            }, f, indent=2)
        
        print("Results saved to repository")
    except Exception as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    run_twitter_bot()
