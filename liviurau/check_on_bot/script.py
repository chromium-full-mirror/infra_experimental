import os
import concurrent.futures

def get_bots():
    stream = os.popen(
        'swarming.py bots -S https://chromium-swarm.appspot.com -d pool chromium.tests -d os Windows-7-SP1 -d cpu x86-64 -d cores 8 -b')
    output = stream.read()
    return output.split('\n')

def check_on_bot(bot):
    stream = os.popen(
        'swarming.py run -S https://chromium-swarm.appspot.com -I https://isolateserver.appspot.com --priority 25 --expiration 7200 --io-timeout 1200 --hard-timeout 2700 -d id '+
        bot +
        ' -d pool chromium.tests --isolated 204e6a43aab267d98754de1f9c9f18ec9f7ba020 --task-summary-json summary1.json --raw-cmd -- out/build/cctest --list')
    output = stream.read()
    if "-1073741511" in output:
        print(bot)
        print("\n")

with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
    executor.map(check_on_bot, get_bots())