# NBA Coaches Challenge Analysis

Recent rule changes in the NBA have allowed for head coaches to challenge a referee's call when they disagree with a call on the floor. If the challenge is unsuccessful (referee was correct initially), the team loses a timeout and they cannot challenge any other calls. If the call is successfully overturned, the team keeps their timeout and is allowed to challenge one more call later in the game if they please.

The purpose of this analysis is to understand the value of a challenge and learn the best situations in which a coach should consider using their challenge -- just because a coach knows a call is incorrect doesn't necessarily the payoff in successfully overturning the call is worth it.

Leveraging NBA win probability data from Mike Beuoy (@inpredict on X, inpredictable.com), we can observe the impact overturned calls may have on the outcome of a game.


### Rank Ordering Challenges

The first step to determining the value of challenges is a simple understanding of the different factors that could affect a change in expected win probability:

  1. What types of outcomes may we see from an overturned call?
  2. What are the chances the call is successfully overturned?
  3. How much time is remaining in the game?
  4. What is the score of the game?
  5. Is the team playing at home or away?
  6. What is the betting spread of the game?
  

### Understanding the trade-off between using and saving your challenge

The second step of this project is to create a tool that takes a game state as input and assesses whether or not the team should use their challenge. This decision requires an understanding of the opportunity cost of saving your challenge for later.


## File Structure

All code within the repository can be found within the 'src' folder