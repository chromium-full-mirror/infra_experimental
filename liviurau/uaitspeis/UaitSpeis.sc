#!/usr/bin/env scala
import sys.process._
import collection.JavaConverters._
import scala.language.postfixOps
import scala.concurrent._
import scala.concurrent.duration.Duration
import scala.concurrent.ExecutionContext.Implicits.global
import java.io.FileWriter
import scala.util.Random
import java.io.BufferedWriter
import java.io.File
import scala.util.Using
import scala.language.implicitConversions
import scala.collection.mutable.ListBuffer



object Main extends App {
    val remoteOrigin = "git config --get remote.origin.url" !!*

    val branch = getBranch
    val upstream = getUpstream(remoteOrigin, branch)

    "git fetch" !!*

    s"git checkout $branch" !!*
    
    "git checkout -b __whitespace" !!*

    s"git branch --set-upstream-to=$upstream" !!*

    touchWhitespaceFile(remoteOrigin)
    
    "git commit -am \"Whitespace to trigger builders\"" !!*

    val extraOptions = getExtraOptions(remoteOrigin)

    s"git cl upload  --bypass-hooks $extraOptions -d --message-file=${messageFilePath}" !!*

    s"git checkout $branch" !!*

    "git branch -D __whitespace" !!*

    def messageFilePath = {
        val messageFile = File.createTempFile("message",".txt"); 
        Using(new FileWriter(messageFile)) {
            _.write("""Whitespace to trigger builders
                      |
                      |R=rubber-stamper@appspot.gserviceaccount.com
                      |
                      |No-Presubmit: true
                      |No-Tree-Checks: true
                      |No-Try: true""".stripMargin)
        }
        messageFile.toPath
    }

    def whitespaceFiles(remote:String) = remote match {
        case "https://chrome-internal.googlesource.com/devtools/devtools-internal" =>
            "/dwarf_extension/tools/whitespace.txt"
        case "https://chromium.googlesource.com/devtools/devtools-frontend.git" =>
            "/scripts/whitespaces.txt"
        case "https://chromium.googlesource.com/v8/v8.git" =>
            "/tools/whitespace.txt"
    }

    def getUpstream(remote:String, branch:String) = remote match {
        case "https://chromium.googlesource.com/v8/v8.git" =>
            s"$branch"
        case _ =>
            s"origin/$branch"
    }

    def getExtraOptions(remote:String) = remote match {
        case "https://chromium.googlesource.com/v8/v8.git" =>
            ""
        case _ =>
            "-a"
    }

    def touchWhitespaceFile(remote:String) = {
        val location = getCwd + whitespaceFiles(remote)
        val randomNumber = Random.nextInt(8) + 2
        Using(new BufferedWriter(new FileWriter(new File(location), true))) {
            _.append(s"No good text, but numbers ... $randomNumber!\n")
        }
    }

    def getBranch = {
        if(args.size != 0) {
            args(0)
        } else {
            "main"
        }
    }

    def getCwd = {
        "git rev-parse --show-toplevel" !!*
    }

    implicit class StringImprovements(val s: String) {
        def !!* = {
            println
            println(s)
            val stdBuffer = new ListBuffer[String]()
            val errBuffer = new ListBuffer[String]()
            val p = s.run(ProcessLogger(stdBuffer.addOne, errBuffer.addOne))
            if(p.exitValue != 0) {
                println(stdBuffer.mkString("\n"))
                println(errBuffer.mkString("\n"))
                System.exit(1)
            }
            val result = stdBuffer.mkString("\n")
            println(result)
            result.trim
        }
    }
}