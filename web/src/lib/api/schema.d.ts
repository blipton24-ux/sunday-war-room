/**
 * GENERATED FILE. Do not edit by hand.
 * Source: api/openapi.json (FastAPI). Regenerate with `npm run generate:api`.
 */

export interface paths {
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Me
         * @description The signed-in user and the leagues they follow.
         */
        get: operations["get_me"];
        put?: never;
        post?: never;
        /**
         * Delete Me
         * @description Delete the account and everything owned by it.
         *
         *     Memberships, platform links and Auth.js sessions cascade from `users`. Shared league and
         *     NFL data stay: they belong to no single user.
         */
        delete: operations["delete_me"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platforms/sleeper/connect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Connect Sleeper
         * @description Look up a Sleeper username and its leagues for the current season.
         *
         *     Runs in the worker (the API never calls Sleeper during a request). Poll
         *     GET /api/v1/jobs/{job_id}; when done, `result.leagues` lists what can be followed.
         */
        post: operations["connect_sleeper"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platforms/espn/probe": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Probe Espn League
         * @description Is a pasted ESPN league public? (ADR-051: league link first.)
         *
         *     Poll GET /api/v1/jobs/{job_id}. The result is one of: `public` (with `leagues` and `teams`),
         *     `private` (ask for the cookies), or `unsupported` (a league type we can't score yet).
         */
        post: operations["probe_espn_league"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platforms/espn/credentials": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Connect Espn
         * @description Save the user's ESPN cookies (encrypted) and list their leagues (ADR-051, ADR-052).
         *
         *     The cookies are stored here and only the account id is queued, because job arguments are kept
         *     unencrypted in Redis. Poll GET /api/v1/jobs/{job_id}; when done, `result.leagues` lists the
         *     user's ESPN leagues, each with `team_id` (the user's own team). The cookies are never returned
         *     by any endpoint.
         */
        post: operations["connect_espn"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/platforms/espn": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Disconnect Espn
         * @description Forget the user's stored ESPN cookies.
         *
         *     Leagues followed with those cookies stay followed but ask to reconnect; an account no league
         *     uses is removed outright.
         */
        delete: operations["disconnect_espn"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Leagues */
        get: operations["list_leagues"];
        put?: never;
        /**
         * Follow League
         * @description Follow a league the user's connect step offered, then sync it.
         *
         *     Sleeper: from the latest username lookup. ESPN: from a public-link probe, or from the league
         *     list a cookie connect returned (then this follow reads the league with the user's own cookies).
         */
        post: operations["follow_league"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/teams": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Teams
         * @description Teams in a league (for choosing "my team").
         */
        get: operations["list_teams"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Unfollow League */
        delete: operations["unfollow_league"];
        options?: never;
        head?: never;
        /** Set My Team */
        patch: operations["set_my_team"];
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh League
         * @description Queue a sync now. Returns the running job if one is already in flight.
         *
         *     Rate limited per user per league (REFRESH_MIN_INTERVAL_SECONDS), counted from when the
         *     user's last refresh finished, so a slow sync does not shorten the wait.
         */
        post: operations["refresh_league"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Job
         * @description Status of a background job. Visible to whoever asked for it, or to members of its league.
         */
        get: operations["get_job"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/matchup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Matchup
         * @description Head-to-head: both lineups with projections and ranges, win probability, scores.
         */
        get: operations["get_matchup"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/lineup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Lineup
         * @description My lineup: current vs optimal, swap suggestions, win chance before/after.
         */
        get: operations["get_lineup"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/accuracy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Accuracy
         * @description How frozen, pre-kickoff projections compared with actual results in past weeks.
         *
         *     One model version at a time: the current one unless `model_version` names another.
         */
        get: operations["get_accuracy"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/players/{player_id}/projection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Player Projection
         * @description One player's projection with every factor, range, and recent games.
         */
        get: operations["get_player_projection"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/waivers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Waivers
         * @description Free agents ranked by points they'd add to my best lineup, with a suggested drop,
         *     waiver status and (FAAB leagues) a bid guide (ADR-047).
         */
        get: operations["get_waivers"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/trades/rosters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Trade Rosters
         * @description Every team's roster with rest-of-season points per week, to build a trade from.
         */
        get: operations["get_trade_rosters"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/trades/evaluate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Evaluate Trade
         * @description Lineup impact of a trade between any two teams in the league (ADR-048).
         */
        post: operations["evaluate_trade"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/leagues/{league_id}/trades/suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Trade Suggestions
         * @description Trades that help my lineup most while the other team loses at most `max_loss`.
         */
        get: operations["get_trade_suggestions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health
         * @description Liveness check (no auth).
         */
        get: operations["health"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccuracyOut */
        AccuracyOut: {
            /** League Id */
            league_id: number;
            /** Model Version */
            model_version: string;
            /** N */
            n: number;
            /** Mae */
            mae: number | null;
            /** Bias */
            bias: number | null;
            /** Coverage 80 */
            coverage_80: number | null;
            /** By Position */
            by_position: {
                [key: string]: {
                    [key: string]: number;
                };
            };
            /** Weeks */
            weeks: components["schemas"]["AccuracyWeek"][];
            /**
             * Available Versions
             * @default []
             */
            available_versions: string[];
        };
        /** AccuracyWeek */
        AccuracyWeek: {
            /** Week */
            week: number;
            /** N */
            n: number;
            /** Mae */
            mae: number;
            /** Coverage 80 */
            coverage_80: number;
        };
        /**
         * ErrorOut
         * @description Every error the API returns has this shape (app/errors.py).
         */
        ErrorOut: {
            /** Detail */
            detail: string;
            /** Code */
            code: string;
        };
        /**
         * EspnCredentialsIn
         * @description The two ESPN cookies (ADR-051). SecretStr keeps them out of validation-error echoes.
         */
        EspnCredentialsIn: {
            /**
             * Espn S2
             * Format: password
             */
            espn_s2: string;
            /**
             * Swid
             * Format: password
             */
            swid: string;
        };
        /**
         * EspnProbeIn
         * @description A pasted league link (or just the league id): is the league public?
         */
        EspnProbeIn: {
            /** Link */
            link: string;
        };
        /** Factor */
        Factor: {
            /** Name */
            name: string;
            /** Value */
            value: number;
            /** Effect */
            effect: number;
            /** Note */
            note: string;
        };
        /** FollowLeagueIn */
        FollowLeagueIn: {
            /**
             * Platform
             * @enum {string}
             */
            platform: "sleeper" | "espn";
            /** External Id */
            external_id: string;
        };
        /** FollowLeagueOut */
        FollowLeagueOut: {
            league: components["schemas"]["LeagueOut"];
            /** Job Id */
            job_id: string;
        };
        /** GameLine */
        GameLine: {
            /** Week */
            week: number;
            /** Opponent */
            opponent: string | null;
            /** Points */
            points: number;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /** Status */
            status: string;
        };
        /** JobOut */
        JobOut: {
            /** Job Id */
            job_id: string;
            /** Kind */
            kind: string;
            /** Status */
            status: string;
            /** League Id */
            league_id: number | null;
            /** Error */
            error: string | null;
            /** Result */
            result: {
                [key: string]: unknown;
            } | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finished At */
            finished_at: string | null;
        };
        /** LeagueOut */
        LeagueOut: {
            /** Id */
            id: number;
            /** Platform */
            platform: string;
            /** External Id */
            external_id: string;
            /** Season */
            season: number;
            /** Name */
            name: string;
            /** Avatar Url */
            avatar_url: string | null;
            /** Current Week */
            current_week: number | null;
            /** My Team Id */
            my_team_id: number | null;
            /** Last Synced At */
            last_synced_at: string | null;
            /** Sync Status */
            sync_status: string | null;
            /**
             * Needs Reconnect
             * @default false
             */
            needs_reconnect: boolean;
        };
        /** LineupOut */
        LineupOut: {
            /** League Id */
            league_id: number;
            /** Week */
            week: number;
            /** As Of */
            as_of: string | null;
            /** Model Version */
            model_version: string;
            /** Starters */
            starters: components["schemas"]["PlayerLine"][];
            /** Bench */
            bench: components["schemas"]["PlayerLine"][];
            /** Optimal */
            optimal: [
                string,
                number | null
            ][];
            /** Swaps */
            swaps: components["schemas"]["SwapOut"][];
            /** Current Points */
            current_points: number;
            /** Optimal Points */
            optimal_points: number;
            /** Win Probability Current */
            win_probability_current: number | null;
            /** Win Probability Optimal */
            win_probability_optimal: number | null;
        };
        /** LineupSlot */
        LineupSlot: {
            /** Slot */
            slot: string;
            player: components["schemas"]["PlayerRef"] | null;
            /** Points Per Week */
            points_per_week: number;
        };
        /** MatchupOut */
        MatchupOut: {
            /** League Id */
            league_id: number;
            /** Week */
            week: number;
            /** As Of */
            as_of: string | null;
            /** Model Version */
            model_version: string;
            me: components["schemas"]["TeamSide"];
            opponent: components["schemas"]["TeamSide"] | null;
            outlook: components["schemas"]["WinOutlook"] | null;
            /** Unsupported Rules */
            unsupported_rules: string[];
            /**
             * Live
             * @default false
             */
            live: boolean;
            /** Clock Source */
            clock_source?: ("scoreboard" | "kickoff_estimate") | null;
            /** Scores Updated At */
            scores_updated_at?: string | null;
        };
        /** MeOut */
        MeOut: {
            /** Id */
            id: number;
            /** Email */
            email: string | null;
            /** Name */
            name: string | null;
            /** Image */
            image: string | null;
            /** Plan */
            plan: string;
            /** Sleeper Username */
            sleeper_username: string | null;
            /** Platforms */
            platforms: components["schemas"]["PlatformOut"][];
            /** Memberships */
            memberships: components["schemas"]["MembershipOut"][];
        };
        /** MembershipOut */
        MembershipOut: {
            /** League Id */
            league_id: number;
            /** League Name */
            league_name: string;
            /** Platform */
            platform: string;
            /** Season */
            season: number;
            /** My Team Id */
            my_team_id: number | null;
            /** Last Synced At */
            last_synced_at: string | null;
        };
        /**
         * PlatformOut
         * @description A connected platform account. Never carries the stored credentials.
         */
        PlatformOut: {
            /** Platform */
            platform: string;
            /** Display Name */
            display_name: string | null;
            /** Status */
            status: string;
        };
        /** PlayerLine */
        PlayerLine: {
            /** Player Id */
            player_id: number;
            /** Name */
            name: string;
            /** Position */
            position: string | null;
            /** Nfl Team */
            nfl_team: string | null;
            /** Headshot Url */
            headshot_url: string | null;
            /** Slot */
            slot: string;
            /** Injury Status */
            injury_status: string | null;
            /** Opponent */
            opponent: string | null;
            /** Kickoff At */
            kickoff_at: string | null;
            /**
             * Game Status
             * @enum {string}
             */
            game_status: "upcoming" | "in_progress" | "final" | "bye";
            projection: components["schemas"]["ProjectionOut"] | null;
            /** Actual Points */
            actual_points: number | null;
            /** Live Points */
            live_points?: number | null;
            /** Game Detail */
            game_detail?: string | null;
            /**
             * Has Ball
             * @default false
             */
            has_ball: boolean;
            /** Remaining Fraction */
            remaining_fraction?: number | null;
        };
        /** PlayerProjectionOut */
        PlayerProjectionOut: {
            player: components["schemas"]["PlayerLine"];
            /** Factors */
            factors: components["schemas"]["Factor"][];
            /** Recent Games */
            recent_games: components["schemas"]["GameLine"][];
            /** Unsupported Rules */
            unsupported_rules: string[];
        };
        /** PlayerRef */
        PlayerRef: {
            /** Player Id */
            player_id: number;
            /** Name */
            name: string;
            /** Position */
            position: string | null;
            /** Nfl Team */
            nfl_team: string | null;
            /** Headshot Url */
            headshot_url: string | null;
            /** Injury Status */
            injury_status: string | null;
        };
        /** ProjectionOut */
        ProjectionOut: {
            /** Points */
            points: number;
            /** P10 */
            p10: number;
            /** P50 */
            p50: number;
            /** P90 */
            p90: number;
            /** Frozen */
            frozen: boolean;
            /**
             * Computed At
             * Format: date-time
             */
            computed_at: string;
            /** Model Version */
            model_version: string;
        };
        /** RosterPlayer */
        RosterPlayer: {
            player: components["schemas"]["PlayerRef"];
            /** Slot */
            slot: string;
            /** Points Per Week */
            points_per_week: number;
        };
        /** SetMyTeamIn */
        SetMyTeamIn: {
            /** My Team Id */
            my_team_id: number;
        };
        /** SleeperConnectIn */
        SleeperConnectIn: {
            /** Username */
            username: string;
        };
        /** SwapOut */
        SwapOut: {
            /** Slot */
            slot: string;
            player_in: components["schemas"]["PlayerLine"];
            player_out: components["schemas"]["PlayerLine"] | null;
            /** Gain */
            gain: number;
        };
        /** TeamOut */
        TeamOut: {
            /** Id */
            id: number;
            /** External Id */
            external_id: string;
            /** Name */
            name: string;
            /** Owner Name */
            owner_name: string | null;
            /** Owner External Id */
            owner_external_id: string | null;
            /** Avatar Url */
            avatar_url: string | null;
            /** Wins */
            wins: number;
            /** Losses */
            losses: number;
            /** Ties */
            ties: number;
        };
        /** TeamSide */
        TeamSide: {
            /** Team Id */
            team_id: number;
            /** Name */
            name: string;
            /** Owner Name */
            owner_name: string | null;
            /** Avatar Url */
            avatar_url: string | null;
            /** Record */
            record: string;
            /** Score */
            score: number | null;
            /** Projected Total */
            projected_total: number;
            /** Starters */
            starters: components["schemas"]["PlayerLine"][];
        };
        /** TradeEvaluateIn */
        TradeEvaluateIn: {
            /** Team A Id */
            team_a_id: number;
            /** Team B Id */
            team_b_id: number;
            /** A Gives */
            a_gives: number[];
            /** B Gives */
            b_gives: number[];
        };
        /** TradeEvaluationOut */
        TradeEvaluationOut: {
            /** League Id */
            league_id: number;
            /** Horizon Weeks */
            horizon_weeks: number[];
            a: components["schemas"]["TradeSideOut"];
            b: components["schemas"]["TradeSideOut"];
        };
        /** TradeIdeaOut */
        TradeIdeaOut: {
            /** Other Team Id */
            other_team_id: number;
            /** Other Team Name */
            other_team_name: string;
            /** Gives */
            gives: components["schemas"]["PlayerRef"][];
            /** Gets */
            gets: components["schemas"]["PlayerRef"][];
            /** My Change Per Week */
            my_change_per_week: number;
            /** Their Change Per Week */
            their_change_per_week: number;
        };
        /** TradeRostersOut */
        TradeRostersOut: {
            /** League Id */
            league_id: number;
            /** Week */
            week: number;
            /** Horizon Weeks */
            horizon_weeks: number[];
            /**
             * League Kind
             * @enum {string}
             */
            league_kind: "redraft" | "keeper" | "dynasty";
            /** Trades Allowed */
            trades_allowed: boolean;
            /** Trade Deadline */
            trade_deadline: number | null;
            /** Deadline Passed */
            deadline_passed: boolean;
            /** Teams */
            teams: components["schemas"]["TradeTeam"][];
            /** Ready */
            ready: boolean;
        };
        /** TradeSideOut */
        TradeSideOut: {
            /** Team Id */
            team_id: number;
            /** Name */
            name: string;
            /** Gives */
            gives: components["schemas"]["PlayerRef"][];
            /** Gets */
            gets: components["schemas"]["PlayerRef"][];
            /** Before Per Week */
            before_per_week: number;
            /** After Per Week */
            after_per_week: number;
            /** Change Per Week */
            change_per_week: number;
            /** Dropped */
            dropped: components["schemas"]["PlayerRef"][];
            /** Lineup Before */
            lineup_before: components["schemas"]["LineupSlot"][];
            /** Lineup After */
            lineup_after: components["schemas"]["LineupSlot"][];
        };
        /** TradeSuggestionsOut */
        TradeSuggestionsOut: {
            /** League Id */
            league_id: number;
            /** Max Loss Per Week */
            max_loss_per_week: number;
            /** Ideas */
            ideas: components["schemas"]["TradeIdeaOut"][];
            /** Ready */
            ready: boolean;
        };
        /** TradeTeam */
        TradeTeam: {
            /** Team Id */
            team_id: number;
            /** Name */
            name: string;
            /** Owner Name */
            owner_name: string | null;
            /** Avatar Url */
            avatar_url: string | null;
            /** Is Mine */
            is_mine: boolean;
            /** Players */
            players: components["schemas"]["RosterPlayer"][];
        };
        /** WaiverPlayer */
        WaiverPlayer: {
            player: components["schemas"]["PlayerRef"];
            /** Gain */
            gain: number;
            /** Gain Per Week */
            gain_per_week: number;
            /** Points Per Week */
            points_per_week: number;
            /**
             * Status
             * @enum {string}
             */
            status: "free_agent" | "waivers";
            /** On Waivers Until */
            on_waivers_until: string | null;
            drop: components["schemas"]["PlayerRef"] | null;
            /** Bid Low */
            bid_low: number | null;
            /** Bid High */
            bid_high: number | null;
        };
        /** WaiversOut */
        WaiversOut: {
            /** League Id */
            league_id: number;
            /** Week */
            week: number;
            /**
             * Horizon
             * @enum {string}
             */
            horizon: "ros" | "week";
            /** Horizon Weeks */
            horizon_weeks: number[];
            /** Playoff Weeks */
            playoff_weeks: number[];
            /**
             * Waiver Kind
             * @enum {string}
             */
            waiver_kind: "rolling" | "reverse_standings" | "faab" | "none";
            /** Faab Budget */
            faab_budget: number | null;
            /** Faab Remaining */
            faab_remaining: number | null;
            /** My Waiver Position */
            my_waiver_position: number | null;
            /** Clear Days */
            clear_days: number;
            /** Players */
            players: components["schemas"]["WaiverPlayer"][];
            /** Ready */
            ready: boolean;
        };
        /** WinOutlook */
        WinOutlook: {
            /** Win Probability */
            win_probability: number;
            /** My Median */
            my_median: number;
            /** Opponent Median */
            opponent_median: number;
            /** My Range */
            my_range: [
                number,
                number
            ];
            /** Opponent Range */
            opponent_range: [
                number,
                number
            ];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    get_me: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MeOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    delete_me: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    connect_sleeper: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SleeperConnectIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    probe_espn_league: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EspnProbeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    connect_espn: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EspnCredentialsIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    disconnect_espn: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    list_leagues: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeagueOut"][];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    follow_league: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FollowLeagueIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FollowLeagueOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    list_teams: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamOut"][];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    unfollow_league: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    set_my_team: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetMyTeamIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeagueOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    refresh_league: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_job: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_matchup: {
        parameters: {
            query?: {
                /** @description Defaults to the current week */
                week?: number | null;
            };
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchupOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_lineup: {
        parameters: {
            query?: {
                /** @description Defaults to the current week */
                week?: number | null;
            };
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LineupOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_accuracy: {
        parameters: {
            query?: {
                model_version?: string | null;
            };
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccuracyOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_player_projection: {
        parameters: {
            query: {
                /** @description Scores with this league's rules */
                league_id: number;
                /** @description Defaults to the current week */
                week?: number | null;
            };
            header?: never;
            path: {
                player_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlayerProjectionOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_waivers: {
        parameters: {
            query?: {
                /** @description Rest of season (default) or this week */
                horizon?: "ros" | "week";
            };
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WaiversOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_trade_rosters: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TradeRostersOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    evaluate_trade: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TradeEvaluateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TradeEvaluationOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    get_trade_suggestions: {
        parameters: {
            query?: {
                /** @description Most the other team may lose, in points per week */
                max_loss?: number;
            };
            header?: never;
            path: {
                league_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TradeSuggestionsOut"];
                };
            };
            /** @description Missing, invalid or expired token */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not found (also returned for another user's league) */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Not ready yet (e.g. first sync unfinished, or no team chosen) */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Invalid request */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
            /** @description Rate limited */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorOut"];
                };
            };
        };
    };
    health: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
