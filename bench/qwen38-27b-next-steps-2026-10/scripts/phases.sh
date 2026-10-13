#!/usr/bin/env bash
# Phase table of the Qwen3.8-27B next-steps campaign. Sourced by run-campaign.sh; no side effects.
# Each phase: PHASE_<id>_ARMS (space-separated arms, reference first), PHASE_<id>_CTXS, PHASE_<id>_BASE
# (reference arm for decide.py), PHASE_<id>_RULE (decide.py args), PHASE_<id>_SKIP (decide.py --skip-gates or "").
# Speed phases run every arm at xhigh (tag p<N>x) and medium (tag p<N>m), 3 reps, bands 32K then 128K.
# bash 3.2 (the rig's /bin/bash): plain strings and indexed arrays only, no associative arrays.
PHASES=(P0 P1 P2 P3 P4 P6)

PHASE_P0_ARMS="s27r";              PHASE_P0_CTXS="32768 131072"; PHASE_P0_BASE="";     PHASE_P0_RULE="";                              PHASE_P0_SKIP=""
PHASE_P1_ARMS="k27";               PHASE_P1_CTXS="32768 131072"; PHASE_P1_BASE="s27r"; PHASE_P1_RULE="--mode le --threshold 0.75";    PHASE_P1_SKIP="hit_append,hit_tool_turn"
PHASE_P2_ARMS="o27q8 o27q4";       PHASE_P2_CTXS="32768 131072"; PHASE_P2_BASE="s27r"; PHASE_P2_RULE="--mode le --threshold 1.00";    PHASE_P2_SKIP=""
PHASE_P3_ARMS="r27d r27m";         PHASE_P3_CTXS="32768 131072"; PHASE_P3_BASE="s27r"; PHASE_P3_RULE="--mode le --threshold 1.00";    PHASE_P3_SKIP=""
PHASE_P4_ARMS="o27sw";             PHASE_P4_CTXS="32768 131072"; PHASE_P4_BASE="o27q4"; PHASE_P4_RULE="--mode le --threshold 1.03";   PHASE_P4_SKIP=""
PHASE_P6_ARMS="l27n l27";          PHASE_P6_CTXS="32768 65536";  PHASE_P6_BASE="s27r"; PHASE_P6_RULE="--mode le --threshold 1.00 --ctx 32768"; PHASE_P6_SKIP="hit_append,hit_tool_turn"

# Reference arm whose p0x files feed every decision against it; the base glob is derived from it.
REF_ARM=s27r; REF_TAG=p0x
# Driver ratio that reopens the driver verdict (spec): T_turno <= 1.25 x w1 (7.9 / 8.6 s).
W1_T32=7.9; W1_T128=8.6; DRIVER_RATIO=1.25
# Arms whose runtime may not report cached_tokens (Splash, llama.cpp): driver_gate ignores their hit gates.
DRIVER_SKIP_HIT_ARMS=k27,l27,l27n
