#!/bin/bash

# See https://unix.stackexchange.com/questions/30286/can-i-configure-my-linux-system-for-more-aggressive-file-system-caching

set -ex

D=vda

echo bfq > /sys/block/$D/queue/scheduler
echo 10000 > /sys/block/$D/queue/iosched/fifo_expire_async
echo 250 > /sys/block/$D/queue/iosched/fifo_expire_sync
echo 80 > /sys/block/$D/queue/iosched/slice_async
echo 1 > /sys/block/$D/queue/iosched/low_latency
echo 6 > /sys/block/$D/queue/iosched/quantum
echo 5 > /sys/block/$D/queue/iosched/slice_async_rq
echo 3 > /sys/block/$D/queue/iosched/slice_idle
echo 100 > /sys/block/$D/queue/iosched/slice_sync
hdparm -q -M 254 /dev/$D



