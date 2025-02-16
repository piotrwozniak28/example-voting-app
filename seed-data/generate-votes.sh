#!/bin/sh

# create votes
ab -n 100 -c 50 -p postb -T "application/x-www-form-urlencoded" http://vote/
ab -n 100 -c 50 -p posta -T "application/x-www-form-urlencoded" http://vote/
ab -n 100 -c 50 -p postb -T "application/x-www-form-urlencoded" http://vote/
