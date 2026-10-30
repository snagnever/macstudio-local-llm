Before you edit anything, map the repository with two Explore subagents running in parallel: call the `Agent` tool twice in the same message, one to list every file the change touches and its callers, one to list the tests and fixtures that exercise that code. Wait for both, then proceed.

