#!/bin/sh
redis-cli ping | grep -q PONG
