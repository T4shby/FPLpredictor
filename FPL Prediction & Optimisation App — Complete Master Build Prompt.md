# FPL Prediction & Optimisation App — Complete Master Build Prompt

You are acting as a senior quantitative developer, data scientist, football analytics engineer, database architect, DevOps engineer and full-stack software engineer.

Your task is to design and build a production-quality Fantasy Premier League analytics application that predicts the **best FPL player selections for each Gameweek**, explains the reasoning behind those predictions, backtests its own performance, and eventually optimises a user's entire FPL team.

The system will run on an **Ubuntu VPS with 16 GB RAM** and must be designed specifically for that environment.

The project must be developed in an **agentic style**: investigate, plan, implement, test, validate, document and iterate proactively rather than waiting for step-by-step human instructions.

The priority is not creating a flashy dashboard.

The priority is creating a **genuinely predictive, statistically defensible and maintainable FPL decision engine**.

---

# 1. Core Objective

For every active Fantasy Premier League player, estimate:

```text
Expected FPL Points (xPts)
```

for:

- Next Gameweek
- Next 3 Gameweeks
- Next 5 Gameweeks

The application should answer questions such as:

- Who are the best players this week?
- Who is the best captain?
- Who is the best vice-captain?
- Who is the best value pick?
- Who is the best differential?
- Which defenders have the best clean-sheet opportunity?
- Which attackers have the best scoring opportunity?
- Which goalkeeper is most attractive?
- Which player is a good one-week punt?
- Which player is a better long-term transfer?
- Who should a user transfer in?
- Who should a user transfer out?
- Is taking a -4 hit mathematically worthwhile?
- What is the strongest legal FPL squad for £100m?
- What should the user's optimal starting XI be?
- Who should be benched?
- Who should be captain and vice-captain?
- Which players have the strongest next 3 or next 5 Gameweeks?

The central concept should be:

```text
PLAYER ABILITY
×
EXPECTED MINUTES
×
TEAM STRENGTH
×
OPPOSITION STRENGTH/WEAKNESS
×
FIXTURE CONDITIONS
×
FPL SCORING PROFILE
→
EXPECTED FPL POINTS
```

---

# 2. Important Modelling Principle

Do NOT simply predict whether a team will win.

The goal is not:

```text
Will Manchester City beat Leeds?
```

The goal is:

```text
How many Fantasy Premier League points
is each Manchester City and Leeds player
expected to score in this particular fixture?
```

For example, if Manchester City are:

- one of the strongest attacking teams
- playing at home
- facing one of the weakest defensive teams
- projected to score multiple goals
- historically strong in this matchup

then Manchester City attackers should receive a positive fixture adjustment.

Leeds defenders should receive a negative adjustment.

However, historical head-to-head should only be one feature.

Current underlying team strength is much more important.

---

# 3. Confirmed Data Availability

The following data sources have already been verified as usable.

## Current Fantasy Premier League data

Use the public-facing FPL JSON endpoints as the main live source.

Examples:

```text
https://fantasy.premierleague.com/api/bootstrap-static/
https://fantasy.premierleague.com/api/fixtures/
```

Relevant information includes:

- player IDs
- names
- clubs
- positions
- price
- ownership
- transfers in/out
- total points
- Gameweek points
- minutes
- starts
- goals
- assists
- clean sheets
- saves
- yellow cards
- red cards
- bonus
- BPS
- expected goals
- expected assists
- expected goal involvements
- expected goals conceded
- player availability
- chance of playing
- fixtures
- opponent
- home/away
- kickoff
- Gameweek information

These endpoints are publicly accessible but should be treated as **unofficial/undocumented interfaces**.

Do not tightly couple the main application to the upstream JSON format.

Use an ingestion/adaptor layer:

```text
FPL API
   ↓
FPL Adapter / Importer
   ↓
Raw Data Storage
   ↓
Normalised PostgreSQL Database
   ↓
Feature Engineering
   ↓
Prediction Engine
   ↓
Application/API
```

If FPL changes a field, we should be able to repair the importer without rewriting the whole application.

---

# 4. Historical Dataset

Use the historical Fantasy Premier League dataset:

```text
https://github.com/vaastav/Fantasy-Premier-League
```

The 2025/26 season has already been verified.

The historical data contains approximately:

```text
29,757 player/Gameweek records
38 Gameweeks
380 Premier League fixtures
841 player records
20 teams
46 player/Gameweek columns
```

Useful fields include:

- player
- team
- opponent
- Gameweek
- kickoff time
- home/away
- minutes
- starts
- goals
- assists
- xG
- xA
- xGI
- xGC
- clean sheets
- saves
- bonus
- BPS
- FPL points
- price
- ownership
- transfers
- actual match result

Use this dataset to build and backtest the initial models.

---

# 5. Our Own Permanent Data Archive

Do not depend permanently on a third party continuing to archive FPL data.

The application must build its own historical database from the current season onwards.

Persist:

```text
raw FPL responses
players
teams
fixtures
Gameweeks
player statistics
prices
ownership
availability
transfers
fixture status
player status
prediction outputs
model versions
```

Historical snapshots must never be overwritten.

This allows us to create our own permanent dataset for future model development.

---

# 6. Mandatory Daily Data Refresh

The application must automatically obtain new data **every day at 09:00 UK time**.

Use:

```text
Timezone: Europe/London
Schedule: 09:00 every day
```

The schedule must correctly follow:

- GMT
- BST
- daylight-saving changes

Do NOT schedule in fixed UTC if doing so would shift the intended UK local time.

The daily 09:00 job should:

```text
1. Fetch latest FPL data
2. Validate the response
3. Store a raw snapshot
4. Normalise new data
5. Update player statistics
6. Update fixture information
7. Update availability/injury indicators
8. Update price and ownership
9. Recalculate derived features
10. Recalculate fixture ratings
11. Recalculate expected minutes
12. Run the current prediction model
13. Update Next GW / Next 3 / Next 5 projections
14. Refresh user-team recommendations
15. Record model run metadata
16. Log success/failure
```

The application should therefore be fully refreshed before users begin updating their FPL teams during the day.

---

# 7. Gameweek Deadline Snapshot

In addition to the daily 09:00 refresh, preserve a final prediction snapshot before each Gameweek deadline.

This is critical for honest model evaluation.

At or shortly before the FPL deadline:

```text
Freeze prediction set
Record data cutoff
Record model version
Record feature version
Record predicted xPts
Record rankings
Record captain rankings
```

Never regenerate the official historical prediction after the deadline using later information.

---

# 8. Data Leakage — Critical Requirement

Backtesting must be strictly leakage-safe.

When predicting Gameweek N, the model may only use information that existed before the Gameweek N deadline.

For example, when predicting GW10, do NOT use:

- GW10 final statistics
- GW10 actual minutes
- GW10 goals
- GW10 xG
- later injuries
- future price movements
- future transfers
- future results
- season totals incorporating matches after GW9

Correct backtesting procedure:

```text
Available information up to GW N-1
        ↓
Generate features
        ↓
Predict GW N
        ↓
Store prediction
        ↓
Reveal actual GW N result
        ↓
Evaluate
        ↓
Advance to GW N+1
```

Any backtest contaminated by future information is invalid.

---

# 9. Four Initial Models

Build four distinct models.

The purpose is to determine how much predictive improvement is gained as additional information is introduced.

---

# 10. Model A — Form Only

This is the baseline.

Use only recent player performance.

Potential features:

```text
FPL points per 90
points last 3
points last 5
points last 8
minutes
starts
goals
assists
clean sheets
saves
bonus
BPS
recent playing time
```

The model should deliberately exclude fixture strength and expected-statistics enhancements.

Name:

```text
Model A — Form
```

---

# 11. Model B — Form + Fixture

Add team and opponent strength.

## Team attacking strength

Potential inputs:

- goals scored
- goals per match
- home goals
- away goals
- recent attacking form
- recent shots if available
- recent expected goals if permitted at this stage

## Team defensive strength

Potential inputs:

- goals conceded
- clean sheets
- home defensive performance
- away defensive performance
- recent defensive performance

Calculate separate fixture ratings:

```text
ATTACKING FIXTURE RATING
DEFENSIVE FIXTURE RATING
```

Do NOT use only one generic fixture difficulty number.

Example:

```text
Manchester City vs Leeds

Manchester City
Attack Fixture: 94/100
Defence Fixture: 78/100

Leeds
Attack Fixture: 24/100
Defence Fixture: 11/100
```

Name:

```text
Model B — Form + Fixture
```

---

# 12. Model C — Form + Fixture + Expected Statistics

Add expected statistics.

Potential features:

```text
xG
xG/90
xA
xA/90
xGI
xGI/90
xGC
xGC/90
```

Calculate rolling windows:

```text
last 3 matches
last 5 matches
last 8 matches
season-to-date
```

Also calculate team-level:

```text
rolling xG
rolling xGA/xGC
home xG
away xG
home xGA
away xGA
```

Name:

```text
Model C — Form + Fixture + xG
```

---

# 13. Model D — Full Model

Model D is the full candidate prediction system.

Include Models A–C plus contextual information.

## Player features

Potential inputs:

- expected minutes
- probability of starting
- probability of reaching 60 minutes
- recent starts
- substitution patterns
- FPL position
- penalties
- corners
- free kicks
- set-piece involvement
- BPS potential
- bonus propensity
- attacking involvement
- defensive contributions
- save volume for goalkeepers
- recent injury status
- availability
- rotation probability

## Team features

- attack strength
- defence strength
- xG
- xGA
- home strength
- away strength
- clean-sheet probability
- expected goals
- current form

## Opponent features

- defensive weakness
- attacking weakness
- xGA
- xG
- goals conceded
- goals scored
- home/away splits
- recent form

## Match context

Potentially:

- rest days
- fixture congestion
- European fixtures
- cup games
- injuries
- suspensions
- likely rotation
- promoted-team uncertainty
- direct head-to-head

Only use these features if reliable data exists.

Name:

```text
Model D — Full Model
```

---

# 14. Historical Head-to-Head

Include historical team-versus-team performance as a possible feature.

For example:

```text
Previous meetings
Wins
Draws
Losses
Goals scored
Goals conceded
Average total goals
Home/away history
```

However, this feature must NOT dominate.

Managers, players, tactical systems and team quality change.

Initial hypothesis:

```text
H2H influence should be relatively small
```

Do not arbitrarily assume a final percentage.

Backtest:

```text
Full Model with H2H
vs
Full Model without H2H
```

If it adds no predictive value, remove or reduce it.

---

# 15. Time Weighting

More recent performances should generally matter more.

At GW1:

```text
Previous season = very important
Current season = almost no sample
```

At GW20:

```text
Current season = highly important
Previous season = reduced influence
```

Use dynamic weighting.

Do not blindly hard-code arbitrary percentages.

Determine useful weights through backtesting.

Possible methods:

- exponential decay
- rolling weighted means
- Bayesian priors
- season transition weighting

---

# 16. Promoted Teams

Promoted teams need special handling because they have little or no recent Premier League history.

Do not simply assign them the worst rating automatically.

Potential prior information:

- Championship finishing position
- Championship xG if obtainable
- goals scored/conceded
- promotion method
- squad changes
- transfer spending
- historical promoted-team performance
- early Premier League results

As Premier League evidence accumulates, reduce the influence of the promoted-team prior.

---

# 17. Expected Minutes

Expected minutes are one of the most important variables in the entire model.

Estimate:

```text
Probability of starting
Expected minutes
Probability of reaching 60 minutes
```

Potential inputs:

- starts last 3/5/8
- average recent minutes
- substitution patterns
- bench appearances
- injury/availability
- fixture congestion
- recent return from injury
- manager rotation patterns

Begin with an explainable heuristic.

Later test statistical or ML models.

A brilliant player expected to play 20 minutes should not outrank a slightly weaker player expected to play 90 without good reason.

---

# 18. FPL Scoring Components

Where practical, predict FPL points by component.

Estimate:

```text
Appearance points
Goal points
Assist points
Clean sheet points
Save points
Defensive contribution points
Bonus points
Cards
Goals-conceded deductions
Penalty-miss probability
Own-goal risk if modelled
```

Then calculate:

```text
Expected FPL Points =
Expected Appearance
+ Expected Goals
+ Expected Assists
+ Expected Clean Sheet
+ Expected Saves
+ Expected Defensive Contributions
+ Expected Bonus
- Expected Negative Points
```

Use the **current season's official FPL scoring rules**.

Store scoring rules in configurable database/configuration records.

Do not scatter hard-coded scoring constants throughout the source code.

---

# 19. Position-Specific Models

Player positions should not be treated identically.

## Goalkeepers

Important variables:

- clean-sheet probability
- expected saves
- opposition shots
- save rate
- penalty-save probability
- BPS/bonus profile

## Defenders

Important variables:

- clean-sheet probability
- expected minutes
- attacking xG
- attacking xA
- set pieces
- defensive contributions
- BPS profile

## Midfielders

Important variables:

- xG
- xA
- team expected goals
- penalties
- set pieces
- clean-sheet bonus
- expected minutes

## Forwards

Important variables:

- xG
- xA
- shots
- team expected goals
- penalties
- expected minutes
- bonus propensity

---

# 20. Match and Fixture Model

For every Premier League fixture calculate:

```text
Expected Home Goals
Expected Away Goals

Home Clean Sheet Probability
Away Clean Sheet Probability

Home Attacking Opportunity
Away Attacking Opportunity

Home Defensive Opportunity
Away Defensive Opportunity
```

Potential approaches:

- Poisson
- adjusted Poisson
- Elo-style team ratings
- rolling xG attack/defence model
- Bayesian attack/defence model

Begin with simple explainable methods.

Only introduce more sophisticated methods if they improve out-of-sample performance.

---

# 21. Model Evaluation

Do not evaluate solely on whether the predicted #1 player happened to score well.

Use multiple metrics.

## Point prediction

- MAE
- RMSE
- calibration
- predicted vs actual correlation

## Ranking quality

Evaluate:

```text
Top 5 predicted players
Top 10
Top 20
Top 50
```

Measure their actual average points.

Compare against naive benchmarks:

- season points
- recent form
- official FPL fixture difficulty
- ownership
- price
- random selection

---

# 22. Practical FPL Performance Metrics

Also measure practical use cases.

Examples:

```text
Average actual score of model Top 10
Best captain success rate
Average captain score
Average xPts gain from recommended transfers
Differential performance
Best-value performance
```

Eventually simulate:

```text
What would have happened if a manager
followed the model every Gameweek?
```

---

# 23. Model Comparison Dashboard

Backtesting must clearly compare:

| Model | MAE | RMSE | Rank Correlation | Top 10 Avg Actual | Captain Result |
|---|---:|---:|---:|---:|---:|
| Model A | | | | | |
| Model B | | | | | |
| Model C | | | | | |
| Model D | | | | | |

Do not assume Model D automatically wins.

If Model B outperforms Model D, investigate why.

---

# 24. Prediction Explanation Engine

Every player prediction should be explainable.

Example:

```text
Erling Haaland

xPts: 8.7
Overall Rank: #1

Positive Factors
+ Elite xG/90
+ Strong Manchester City attack
+ Weak opponent defence
+ Home fixture
+ Penalty taker
+ 95% projected start
+ Strong expected team goals

Negative Factors
- European fixture three days earlier
- Minor rotation risk
```

Where possible show projected components:

```text
Appearance: 1.9
Goals:      3.5
Assists:    0.6
Clean sheet: 0.2
Bonus:      1.3
Other:      1.2

Total:      8.7
```

The user should understand why a recommendation was made.

---

# 25. Main Dashboard

Display:

- current Gameweek
- next deadline
- latest data refresh
- model version
- best player
- best captain
- best vice-captain
- best differential
- best value
- best goalkeeper
- best defender
- best midfielder
- best forward
- biggest prediction movers
- current data status

---

# 26. Player Rankings

Create a sortable/filterable ranking table.

Suggested columns:

```text
Rank
Player
Team
Position
Opponent
H/A
Price
Ownership
Expected Minutes
Start Probability
Attack Fixture Rating
Defence Fixture Rating
xG/90
xA/90
GW xPts
3GW xPts
5GW xPts
Value Score
Differential Score
```

Filters:

- position
- team
- price
- ownership
- availability
- expected minutes
- fixture quality

---

# 27. Best Picks Categories

Automatically calculate:

```text
Best Overall
Best Captain
Best Vice Captain
Best Value
Best Differential
Best Ultra Differential
Best Goalkeeper
Best Defender
Best Midfielder
Best Forward
Best Budget GK
Best Budget Defender
Best Budget Midfielder
Best Budget Forward
Best One-Week Punt
Best 3-GW Transfer
Best 5-GW Transfer
```

Possible ownership definitions:

```text
Differential < 10%
Ultra Differential < 5%
```

Make thresholds configurable.

---

# 28. Player Detail Page

Show:

```text
Player
Club
Position
Price
Ownership
Availability

xPts GW
xPts Next 3
xPts Next 5

Expected Minutes
Starting Probability

Recent Points
Recent xG
Recent xA
Recent xGI

Upcoming Fixtures
Attack Fixture Ratings
Defensive Fixture Ratings

Prediction Breakdown
Positive Factors
Negative Factors
```

Useful charts:

- actual FPL points
- xPts
- xG
- xA
- minutes
- ownership
- price

---

# 29. Custom Fixture Ticker

Build our own fixture ticker.

Do not simply copy the official FPL FDR.

For every fixture show:

```text
GW
Opponent
Home/Away
Attacking Fixture Rating
Defensive Fixture Rating
Expected Goals
Clean Sheet Probability
```

Views:

```text
Next 1
Next 3
Next 5
Next 8
```

---

# 30. One-Week Pick vs Long-Term Transfer

Explicitly differentiate:

```text
BEST THIS WEEK
```

from:

```text
BEST TRANSFER
```

Example:

```text
Player A

GW xPts: 8.4
3GW xPts: 13.2
5GW xPts: 19.0
```

versus:

```text
Player B

GW xPts: 6.7
3GW xPts: 20.4
5GW xPts: 32.9
```

Player A may be the better Free Hit or one-week punt.

Player B may be the better permanent transfer.

---

# 31. User FPL Team Import

Allow users to enter their FPL team ID where technically possible.

Import relevant squad data.

Potential information:

- squad
- starting XI
- bench
- captain
- vice-captain
- team value
- bank
- transfers
- free transfers where available
- chips where available

Do not invent inaccessible fields.

If some account-specific data cannot be retrieved without authentication, clearly separate what is and is not possible.

---

# 32. My Team Dashboard

For an imported squad calculate:

```text
Recommended Starting XI
Recommended Bench
Recommended Bench Order
Recommended Captain
Recommended Vice Captain
Weakest Current Pick
Best Transfer Target
```

Show predicted:

```text
Current Squad xPts
Optimised XI xPts
```

---

# 33. Transfer Optimiser

Given:

```text
current squad
budget
bank
free transfers
future fixtures
player xPts
FPL rules
```

recommend transfers.

Example:

```text
OUT
Player X

Next 3 xPts: 10.2

IN
Player Y

Next 3 xPts: 18.4

Projected Improvement: +8.2
```

Account for:

- position
- squad budget
- club limits
- player prices
- selling prices where available
- free transfers
- points hits

---

# 34. Hit Calculator

Evaluate:

```text
Expected points gain
-
Transfer hit
```

Example:

```text
Player X → Player Y

Expected gain next 3:
+7.1

Hit:
-4

Net:
+3.1
```

Also include uncertainty.

Do not recommend a -4 because estimated gain is only +0.1.

Use configurable risk/safety thresholds.

---

# 35. Captain Model

Captaincy should have its own ranking.

Consider:

- mean xPts
- ceiling
- goal probability
- assist probability
- expected minutes
- fixture
- penalty duty
- variance

Eventually display:

```text
xPts
P(5+)
P(8+)
P(10+)
P(15+)
```

The captain model should optimise for doubled FPL scoring, not simply replicate the player rankings without analysis.

---

# 36. Differential Model

A differential should combine:

```text
Expected Points
Ownership
Expected Minutes
Fixture Quality
```

Do not reward a bad player merely because ownership is 0.1%.

Require a minimum xPts or quality threshold.

---

# 37. Value Model

Calculate:

```text
xPts per £m
```

but recognise that simple points-per-million can heavily favour cheap players.

Also investigate:

```text
Value Above Replacement
```

by position.

---

# 38. Squad Optimisation

Eventually solve:

```text
Maximise expected FPL points
subject to all FPL squad rules
```

Constraints include:

```text
£100m initial budget
15 players
2 goalkeepers
5 defenders
5 midfielders
3 forwards
maximum 3 players per club
```

Potential methods:

- integer linear programming
- mixed-integer programming

Support:

```text
Best Squad for Next GW
Best Squad for Next 3
Best Squad for Next 5
Wildcard Squad
Free Hit Squad
```

---

# 39. Double and Blank Gameweeks

Support these correctly.

A player can have:

```text
0 fixtures
1 fixture
2+ fixtures
```

in the same Gameweek.

For a Double Gameweek:

```text
GW xPts =
Fixture 1 xPts
+
Fixture 2 xPts
```

while considering rotation/minutes.

For a blank:

```text
xPts = 0
```

unless the player has another scheduled fixture.

Never assume one fixture per player per Gameweek.

---

# 40. Postponed and Rescheduled Fixtures

Fixture ingestion must handle:

- postponements
- cancellations
- rescheduling
- changed Gameweek assignments
- changed kickoff times

The daily import should detect fixture changes and recalculate affected predictions automatically.

---

# 41. Database

Use:

```text
PostgreSQL
```

Suggested schema:

```text
players
teams
fixtures
gameweeks

raw_api_snapshots

player_gameweek_stats
team_gameweek_stats

player_snapshots
team_snapshots

player_expected_minutes
team_ratings
fixture_ratings

derived_features

model_versions
feature_versions
model_runs

player_predictions

backtest_runs
backtest_predictions
backtest_metrics

users
user_fpl_profiles
user_team_snapshots
user_recommendations

system_jobs
system_logs
```

Keep separate:

```text
RAW DATA
NORMALISED DATA
DERIVED FEATURES
MODEL OUTPUTS
ACTUAL RESULTS
```

Never throw away raw source data unnecessarily.

---

# 42. Production Hosting

The production application will run on:

```text
Ubuntu VPS
16 GB RAM
```

Design specifically for a single VPS.

Do not architect for:

- Kubernetes
- giant cloud clusters
- GPU servers
- unnecessarily complicated microservices
- serverless platforms
- expensive managed infrastructure

Prefer simplicity and maintainability.

---

# 43. Recommended Technology Stack

Backend:

```text
Python
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Pandas
NumPy
scikit-learn
SciPy
statsmodels
```

Optional later:

```text
XGBoost
LightGBM
CatBoost
```

Frontend:

```text
React / Next.js
```

Deployment:

```text
Docker
Docker Compose
Nginx or another suitable reverse proxy
```

Background jobs:

```text
Python worker
APScheduler / cron / Celery if justified
```

Redis should only be added if it solves a genuine requirement such as:

- distributed job locking
- cache
- task queue

Do not add infrastructure simply because it is fashionable.

---

# 44. Suggested Production Containers

A reasonable architecture:

```text
fpl-nginx
fpl-frontend
fpl-backend
fpl-worker
fpl-postgres
```

Optional:

```text
fpl-redis
```

only if needed.

---

# 45. VPS Resource Management

The entire system must comfortably fit within 16 GB RAM.

Do not load the complete historical database into RAM unnecessarily.

Prefer:

- SQL aggregation
- incremental calculations
- chunked processing
- indexed tables
- cached features
- efficient Pandas usage
- precomputed historical statistics

Historical Gameweeks should not be recalculated every morning unless necessary.

The daily job should principally process changed/current data.

---

# 46. Backups

Production must have automated backups.

At minimum:

```text
Daily PostgreSQL backup
Configuration backup
Retention policy
Restore documentation
```

Prefer keeping backups outside the live database volume.

The application should provide a documented restore procedure.

---

# 47. Health Monitoring

Provide health endpoints and system status.

Monitor:

```text
Frontend
Backend
Database
Worker
Last successful FPL import
Last prediction run
Next scheduled update
```

The UI should expose something simple such as:

```text
Data Updated:
21 Aug 2026 09:03

Next Refresh:
22 Aug 2026 09:00

Prediction Model:
Model D v0.7.1
```

---

# 48. Failed Daily Update Handling

A failed 09:00 import must not silently break the application.

The system should:

```text
Detect failure
Log the error
Retain previous valid data
Retry automatically
Mark data as stale
Expose warning in admin/system status
```

Do not delete or replace the last known-good prediction set unless a new import and model run succeeds.

Recommended retry behaviour might be:

```text
09:00
09:10
09:30
10:00
```

or another sensible retry policy.

Avoid hammering upstream services.

---

# 49. Data Validation

Every import should run automated validation.

Examples:

```text
Player count within sensible bounds
All teams resolve
No duplicate fixture IDs
No impossible minutes
Valid Gameweeks
Valid player IDs
Valid team IDs
Expected fields present
No unexpected massive null increases
No schema-breaking changes
```

If validation fails:

```text
Reject the new dataset
Keep previous valid snapshot
Log the problem
```

---

# 50. API Change Detection

Because FPL interfaces are unofficial, the importer should detect:

- removed fields
- renamed fields
- changed types
- unexpected nulls
- structural changes

Store raw responses to assist troubleshooting.

Create automated tests around the adapter.

---

# 51. Feature Versioning

Every prediction must retain:

```text
model version
feature version
data cutoff
prediction time
Gameweek
```

Example:

```text
Model: D
Version: 0.4.2

Feature Set:
3.1

Data Cutoff:
2026-09-11 09:00

Target:
GW4
```

This ensures predictions are reproducible.

---

# 52. Never Rewrite Historical Predictions

Once a prediction is frozen for a Gameweek, never silently regenerate it with future information.

Keep:

```text
Original Prediction
Actual Result
Evaluation
```

separately.

---

# 53. Development Philosophy

Start with transparent models.

Do NOT use an LLM as the primary football prediction mechanism.

Progression should be:

```text
Simple statistical baseline
↓
Better engineered features
↓
Regression / Poisson
↓
Bayesian models
↓
Tree-based ML
↓
Ensemble if justified
```

Complexity must earn its place through improved out-of-sample performance.

---

# 54. Machine Learning

Potential later models:

```text
Linear Regression
Ridge
Poisson Regression
Random Forest
Gradient Boosting
XGBoost
LightGBM
CatBoost
```

Use walk-forward validation.

Never optimise only against training performance.

---

# 55. Prediction Uncertainty

Do not present xPts as certainty.

Eventually calculate distributions such as:

```text
Expected Points: 7.8

P(5+)  62%
P(8+)  38%
P(10+) 24%
P(15+) 8%
```

This will be especially useful for:

- captaincy
- differentials
- high-risk punts

---

# 56. Agentic Development Behaviour

The development agents must work proactively.

They should not require the user to provide every individual implementation instruction.

For each significant task, the agent should:

```text
1. Inspect the current repository and architecture
2. Understand what already exists
3. Identify dependencies and risks
4. Form an implementation plan
5. Implement the change
6. Run tests
7. Inspect test failures
8. Fix issues
9. Run relevant integration checks
10. Update documentation
11. Commit/record the completed state if repository workflow permits
12. Move to the next logical task
```

Do not stop after generating code without testing it.

---

# 57. Agent Autonomy

Agents should make sensible technical decisions independently where the requirements already make the intent clear.

Do NOT repeatedly ask questions such as:

```text
Should I create the database table?
Should I add tests?
Should I make the endpoint?
Should I run the migration?
```

If these are clearly necessary to complete the agreed task, do them.

Ask the user only when there is a genuine product/business decision that cannot reasonably be inferred.

---

# 58. Agent Investigation

Before claiming something is impossible or unavailable:

```text
Inspect the code
Inspect the database
Inspect the API
Inspect available documentation
Inspect existing tests
Inspect logs where relevant
```

Do not guess.

Do not fabricate.

If a required external field is uncertain, verify its availability before building around it.

---

# 59. Agent Work Breakdown

For complex work, agents should break the project into manageable workstreams.

Suggested workstreams:

```text
DATA AGENT
MODEL AGENT
BACKTEST AGENT
BACKEND AGENT
FRONTEND AGENT
DEVOPS AGENT
QA AGENT
```

These may be conceptual roles rather than separate processes.

Each workstream should have clear responsibilities.

---

# 60. Data Agent Responsibilities

Responsible for:

```text
FPL API integration
historical imports
normalisation
snapshots
schema-change detection
data validation
data quality reporting
daily refresh
```

---

# 61. Modelling Agent Responsibilities

Responsible for:

```text
feature engineering
expected minutes
team ratings
fixture ratings
Models A-D
xPts calculation
uncertainty
captain model
value model
differential model
```

---

# 62. Backtest Agent Responsibilities

Responsible for:

```text
walk-forward simulation
leakage prevention
model comparison
metrics
historical prediction freezing
diagnostics
```

The backtest agent should actively look for leakage.

---

# 63. Backend Agent Responsibilities

Responsible for:

```text
FastAPI
database models
migrations
application services
authentication if needed
user FPL team import
prediction endpoints
transfer optimisation endpoints
admin/status endpoints
```

---

# 64. Frontend Agent Responsibilities

Responsible for:

```text
dashboard
rankings
player pages
fixture ticker
model explanations
My Team
transfer recommendations
captain recommendations
responsive layout
```

---

# 65. DevOps Agent Responsibilities

Responsible for:

```text
Docker
Docker Compose
Nginx
environment variables
production configuration
daily scheduler
backups
health checks
deployment
logging
resource limits
```

Optimise specifically for the 16 GB Ubuntu VPS.

---

# 66. QA Agent Responsibilities

Responsible for:

```text
unit tests
integration tests
data tests
API tests
regression tests
leakage checks
deployment checks
daily-job simulation
```

A task is not complete merely because code compiles.

---

# 67. Agentic Iteration

When a model performs badly:

do not just report:

```text
Model performed badly.
```

Investigate:

- which positions perform badly
- which Gameweeks perform badly
- whether expected minutes caused error
- whether fixtures are misrated
- whether promoted-team priors are wrong
- whether injuries caused problems
- whether high-variance players dominate error
- whether the model is overfitting
- whether data leakage exists

Then propose and test improvements.

---

# 68. No Fabricated Progress

Agents must not claim:

```text
implemented
tested
working
validated
production ready
```

unless the corresponding work was genuinely completed.

When something remains incomplete, clearly state:

```text
TODO
BLOCKED
NOT YET VERIFIED
```

---

# 69. Repository Structure

Suggested structure:

```text
fpl-app/

backend/
    app/
        api/
        models/
        schemas/
        services/
        db/

data/
    clients/
    ingestion/
    validation/
    snapshots/

features/
    player_form/
    team_strength/
    fixture_strength/
    expected_minutes/
    head_to_head/

modelling/
    model_a/
    model_b/
    model_c/
    model_d/
    scoring/

backtest/
    engine/
    metrics/
    reports/

optimisation/
    transfers/
    captain/
    squad/

worker/
    jobs/
    scheduling/

frontend/

tests/

scripts/

docker/

docs/
```

Keep modules small and logically separated.

---

# 70. Logging

Use structured logging.

Important events:

```text
data import started
data import completed
validation failed
prediction run started
prediction run completed
Gameweek snapshot frozen
backup completed
job failed
retry scheduled
model version changed
```

Avoid noisy logs that provide no diagnostic value.

---

# 71. Administration

Provide a basic admin/system page.

Display:

```text
Current season
Current Gameweek
Next deadline
Last import
Last successful prediction
Database status
Model version
Feature version
Worker status
Latest backup
```

Admin actions may eventually include:

```text
Run Import Now
Recalculate Current Predictions
Run Validation
View Job Logs
```

Protect administrative functions appropriately.

---

# 72. Security

Follow normal production security principles.

At minimum:

```text
No secrets in source control
Environment variables for credentials
Database not publicly exposed
HTTPS
Secure cookies if authentication is added
Input validation
Rate limiting where appropriate
Restricted admin routes
```

---

# 73. Data Source Registry

For every external feature document:

```text
Field
Source
Endpoint/File
Update Frequency
Reliability
Licensing/Usage Notes
Fallback
```

Classify features:

```text
DIRECTLY AVAILABLE
DERIVED
EXTERNAL SOURCE REQUIRED
NOT CURRENTLY AVAILABLE
```

Do not quietly invent data.

---

# 74. Current vs Historical Data

Make a strict distinction between:

```text
Current Live Data
Historical Observed Data
Derived Model Features
Predictions
```

The database and code should make those categories obvious.

---

# 75. First Development Phase — Data Feasibility

Before serious model building:

```text
1. Import full 2025/26 historical dataset
2. Validate fields and row counts
3. Generate data dictionary
4. Identify missing data
5. Categorise every proposed feature
6. Build live FPL importer
7. Save raw snapshots
8. Build normalised tables
```

Produce a report of what is actually available.

---

# 76. Second Development Phase — Backtest Framework

Build the walk-forward engine before building a polished frontend.

Required flow:

```text
GW1 prediction
↓
evaluate
↓
GW2 prediction
↓
evaluate
↓
...
↓
GW38
```

The engine must make future-data leakage difficult by design.

---

# 77. Third Development Phase — Four Models

Implement:

```text
Model A — Form
Model B — Form + Fixture
Model C — Form + Fixture + xG
Model D — Full
```

Backtest them against 2025/26.

---

# 78. First Meaningful Deliverable

Produce a report similar to:

```text
2025/26 BACKTEST

MODEL A — FORM

MAE:
RMSE:
Rank correlation:
Top 10 average actual points:
Captain average:

MODEL B — FORM + FIXTURE

MAE:
RMSE:
Rank correlation:
Top 10 average actual points:
Captain average:

MODEL C — FORM + FIXTURE + xG

MAE:
RMSE:
Rank correlation:
Top 10 average actual points:
Captain average:

MODEL D — FULL

MAE:
RMSE:
Rank correlation:
Top 10 average actual points:
Captain average:
```

Also state which features added value and which did not.

---

# 79. Fourth Development Phase — Current Season Prediction

Once a model has demonstrated useful historical performance:

```text
Import current 2026/27 data
Generate current features
Calculate team ratings
Calculate fixture ratings
Calculate expected minutes
Generate current xPts
```

Then start daily operation.

---

# 80. Fifth Development Phase — Web Application

Only after the prediction pipeline is trustworthy should the primary UI be built.

Initial UI:

```text
Dashboard
Player Rankings
Player Detail
Fixture Ticker
Model Comparison
System Status
```

---

# 81. Sixth Development Phase — Personal Team Tools

Then add:

```text
My Team
Captain Recommendation
Vice-Captain
Bench Order
Transfer Recommendations
Hit Calculator
```

---

# 82. Seventh Development Phase — Optimisation

Then add:

```text
Best £100m Squad
Wildcard Optimiser
Free Hit Optimiser
Multi-Gameweek Transfer Planning
```

---

# 83. Example Production Prediction

The finished application should be able to produce:

```text
GAMEWEEK 6

#1 Erling Haaland
Manchester City
LEE (H)

xPts: 8.7
Price: £14.0m
Ownership: 41%

Expected Minutes: 84
Start Probability: 95%

Attack Fixture: 96/100
Team Expected Goals: 2.8

Projection:
Appearance: 1.9
Goals: 3.5
Assists: 0.6
Bonus: 1.4
Other: 1.3

WHY

+ Elite xG/90
+ Weak opposition defence
+ Home fixture
+ Penalty taker
+ Strong Manchester City attacking rating

RISKS

- European fixture three days earlier
- Small rotation risk
```

---

# 84. Example Transfer Recommendation

```text
BEST TRANSFER — NEXT 3 GAMEWEEKS

OUT
Player A

Price: £7.5m
3GW xPts: 10.8

IN
Player B

Price: £7.2m
3GW xPts: 18.7

Projected Improvement:
+7.9 points

Cost:
1 Free Transfer

Recommendation:
MAKE TRANSFER
```

---

# 85. Current Data Refresh Behaviour

Every day at 09:00 Europe/London:

```text
Fetch
Validate
Persist
Calculate
Predict
Publish
```

Users should not need to manually trigger this.

If the data changes materially during the day because of:

- postponement
- injury
- major availability change

the architecture should permit an administrator to trigger an additional refresh.

Do not initially introduce aggressive high-frequency polling.

Daily 09:00 is the normal automatic refresh.

---

# 86. Performance Expectations

The application should feel responsive even while model processing occurs in the background.

Do not make a user's page request wait for the complete model to recalculate.

Predictions should be precomputed by the worker and stored in PostgreSQL.

The web app should mainly read already-calculated results.

Architecture:

```text
09:00 Worker
      ↓
Calculates predictions
      ↓
PostgreSQL
      ↓
Fast API response
      ↓
Frontend
```

---

# 87. Testing Requirements

Tests should include:

## Data tests

```text
historical imports
live API parsing
fixture parsing
player mapping
team mapping
schema validation
```

## Feature tests

```text
rolling windows
home/away calculations
team ratings
fixture ratings
expected minutes
```

## Model tests

```text
xPts calculations
position scoring
Double Gameweeks
Blank Gameweeks
```

## Leakage tests

Create explicit tests designed to ensure future Gameweek information cannot enter historic features.

## Application tests

```text
API
database migrations
frontend critical paths
worker jobs
09:00 schedule
```

---

# 88. Documentation

Maintain documentation as the agents work.

Required documents:

```text
README.md
ARCHITECTURE.md
DATA_SOURCES.md
DATA_DICTIONARY.md
MODELS.md
BACKTESTING.md
DEPLOYMENT.md
OPERATIONS.md
BACKUP_RESTORE.md
```

Documentation should reflect the actual implementation.

Do not allow it to drift significantly from the codebase.

---

# 89. Decision Log

Maintain a concise technical decision log.

Examples:

```text
Why PostgreSQL was selected
Why H2H weighting was reduced
Why Model C replaced Model B
Why a particular scheduler was used
Why Redis was or was not introduced
```

This will help future agents understand the project.

---

# 90. Core Rules

Throughout the entire project:

1. Never invent unavailable data.
2. Verify external data before designing around it.
3. Never allow future information into historical predictions.
4. Preserve raw source data.
5. Preserve historical predictions.
6. Keep model runs reproducible.
7. Prefer explainable models initially.
8. Backtest every meaningful modelling change.
9. Do not assume added complexity improves predictions.
10. Keep ingestion separate from modelling.
11. Keep modelling separate from presentation.
12. Test critical calculations.
13. Use database migrations.
14. Never hard-code player IDs.
15. Never hard-code team IDs.
16. Handle promoted and relegated teams.
17. Handle club transfers.
18. Handle position changes.
19. Handle blank Gameweeks.
20. Handle Double Gameweeks.
21. Handle fixture rescheduling.
22. Keep scoring rules configurable.
23. Record the model version behind every prediction.
24. Design for Ubuntu + 16 GB RAM.
25. Run the daily update automatically at 09:00 UK time.
26. Prefer reliable simple architecture over unnecessary complexity.
27. Agents should proactively complete logical follow-on work.
28. Agents should test their own implementation.
29. Agents should investigate failures instead of guessing.
30. Do not claim success without verification.

---

# 91. Product Vision

The finished system should combine:

```text
FPL player analysis
+
team-strength modelling
+
fixture modelling
+
player expected-points projections
+
captain selection
+
transfer optimisation
+
squad optimisation
+
personal team analysis
```

The unique value proposition is:

> Instead of simply telling users which teams have easy fixtures, identify which individual FPL players are mathematically best positioned to score points this week and over the coming Gameweeks, show how confident the model is, and explain why.

---

# 92. Immediate Instruction to the Development Agents

Start with the data and modelling foundation.

Do NOT start by spending significant time on visual design.

Perform the following autonomously:

```text
1. Inspect the repository and current environment.
2. Establish the project structure.
3. Import and inspect the verified 2025/26 historical FPL dataset.
4. Produce a proper data dictionary.
5. Categorise proposed features as available, derived, external or unavailable.
6. Build PostgreSQL schemas and migrations.
7. Build the FPL live-data importer.
8. Build raw snapshot storage.
9. Build automated data validation.
10. Implement the 09:00 Europe/London daily refresh architecture.
11. Build the leakage-safe walk-forward backtesting engine.
12. Implement Model A.
13. Backtest Model A.
14. Implement Model B.
15. Backtest Model B.
16. Implement Model C.
17. Backtest Model C.
18. Implement the first transparent version of Model D.
19. Backtest Model D.
20. Compare all four models.
21. Investigate where each model succeeds and fails.
22. Identify the strongest model objectively.
23. Generate current-season predictions.
24. Only then proceed to the core application UI.
```

Work agentically through this sequence.

Where there is a clear logical next action, take it.

Do not stop merely because one individual subtask has completed.

Do not ask the user to make routine engineering decisions that can reasonably be handled by the development team.

Escalate only genuine product decisions, major architecture trade-offs, unavailable data, security concerns or blockers that materially require human input.

The end goal is not merely to produce code.

The end goal is to produce a **self-updating, evidence-driven Fantasy Premier League prediction and optimisation platform running reliably on a 16 GB Ubuntu VPS, refreshed automatically every day at 09:00 UK time, with predictions that can be proven against historical results.**