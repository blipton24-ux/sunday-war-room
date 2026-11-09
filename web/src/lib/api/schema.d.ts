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
         * @description Follow a league found by the user's latest Sleeper connect, then sync it.
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
         *     Rate limited per user per league (REFRESH_MIN_INTERVAL_SECONDS).
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
             * @constant
             */
            platform: "sleeper";
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
