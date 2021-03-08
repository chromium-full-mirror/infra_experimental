import sys.process._
import collection.JavaConverters._
import scala.language.postfixOps
import scala.concurrent._
import scala.concurrent.duration.Duration
import scala.concurrent.ExecutionContext.Implicits.global

object Main extends App {
  def isolateHash = "cb2e85adda70f2ca9b130c164b3fbdf0fc35df33"
  def getBots(): List[String] = {
    val cmd =
      "swarming.py bots -S https://chromium-swarm.appspot.com -d pool chromium.tests -d os Windows-7-SP1 -d cpu x86-64 -d cores 8 -b"
    (cmd !!).split("\n").toList.map(_.trim).filter(_ != "")
  }
  def checkOnBot(bot: String) = {
    val cmd =
      s"swarming.py run -S https://chromium-swarm.appspot.com -I https://isolateserver.appspot.com --priority 25 --expiration 7200 --io-timeout 1200 --hard-timeout 2700 -d id $bot -d pool chromium.tests --isolated $isolateHash --task-summary-json summary1.json --raw-cmd -- out/build/d8.exe --help"
    (cmd !)(ProcessLogger(_ => {}, _ => {}))
  }

  def dumpbinOnBot(bot:String) {
    val cmd =
      s"swarming.py run -S https://chromium-swarm.appspot.com -I https://isolateserver.appspot.com --priority 25 --expiration 7200 --io-timeout 1200 --hard-timeout 2700 -d id $bot -d pool chromium.tests --isolated $isolateHash --task-summary-json summary1.json --raw-cmd -- dumpbin /DEPENDENTS out/build/cctest"
    cmd !
  }

  def psOnBot(bot:String) {
    val psScript = "Get-Item out/build/cctest.exe | ForEach-Object { foreach ($asm in [System.Reflection.Assembly]::LoadFrom($_.FullName).GetReferencedAssemblies()) { echo \"$_.Name - $asm\"} }"
    val cmd =
      s"swarming.py run -S https://chromium-swarm.appspot.com -I https://isolateserver.appspot.com --priority 25 --expiration 7200 --io-timeout 1200 --hard-timeout 2700 -d id $bot -d pool chromium.tests --isolated $isolateHash --task-summary-json summary1.json --raw-cmd -- powershell -command $psScript"
    cmd !
  }

  def run() = {
    var failingBots = List[String]()
    val bots = getBots()
    println("bots:" + bots)
    val maybeFailing = getBots()
      //.drop(15)
      //.take(3)
      .map { bot =>
        Future { (bot, checkOnBot(bot)) }
      }
    val result = Future.sequence(maybeFailing)
    result.onComplete { list =>
      val result = list.get.filter(_._2 == 57).map(_._1).sorted
      println("result:"+result)
      println(result.size)
    }
    Await.ready(result, Duration.Inf)
  }

  run()
  //println(checkOnBot("vm27-m4"))
}
