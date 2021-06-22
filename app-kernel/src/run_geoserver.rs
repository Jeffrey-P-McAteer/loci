
use crate::ensure_file_is_executable;

use shlex;

use std::path::{Path};
use std::process::{Command, Child, Stdio};
use std::fs;

pub const GEOSERVER_PORT: u64 = 8001;

pub fn start(geoserver_home: &Path) -> Result<(String, Child), Box<dyn std::error::Error>> {

  eprintln!("geoserver_home={}", &geoserver_home.to_string_lossy());

  let mut geoserver_home = geoserver_home.to_path_buf();

  let start_ini = if cfg!(windows) {
    format!("{}\\start.ini", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/start.ini", geoserver_home.to_string_lossy())
  };

  // Write our config for geoserver...
  fs::write(start_ini, format!(r#"
# --------------------------------------- 
# Module: server
--module=server

# minimum number of threads
threads.min=2
# maximum number of threads
threads.max=20
# thread idle timeout in milliseconds
threads.timeout=60000
# buffer size for output
jetty.output.buffer.size=32768
# request header buffer size
jetty.request.header.size=8192
# response header buffer size
jetty.response.header.size=8192
# should jetty send the server version header?
jetty.send.server.version=true
# should jetty send the date header?
jetty.send.date.header=false
# What host to listen on (leave commented to listen on all interfaces)
jetty.host=localhost
# Dump the state of the Jetty server, components, and webapps after startup
jetty.dump.start=false
# Dump the state of the Jetty server, before stop
jetty.dump.stop=false
# Enable delayed dispatch optimisation
jetty.delayDispatchUntilContent=false

# --------------------------------------- 
# Module: servlets
--module=servlets

# --------------------------------------- 
# Module: deploy
--module=deploy

# Monitored Directory name (relative to jetty.base)
# jetty.deploy.monitoredDirName=webapps

# --------------------------------------- 
# Module: websocket
#--module=websocket

# --------------------------------------- 
# Module: ext
#--module=ext

# --------------------------------------- 
# Module: resources
--module=resources

# --------------------------------------- 
# Module: http
--module=http

# HTTP port to listen on
jetty.port={GEOSERVER_PORT}

# HTTP idle timeout in milliseconds
http.timeout=21000

# HTTP Socket.soLingerTime in seconds. (-1 to disable)
# http.soLingerTime=-1

# Parameters to control the number and priority of acceptors and selectors
# http.selectors=1
# http.acceptors=1
# http.selectorPriorityDelta=0
# http.acceptorPriorityDelta=0

# --------------------------------------- 
# Module: webapp
--module=webapp

  "#,
    GEOSERVER_PORT=GEOSERVER_PORT,

  ))?;

  // Overwrite jetty config xml
  let web_xml = if cfg!(windows) {
    format!("{}\\webapps\\geoserver\\WEB-INF\\web.xml", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/webapps/geoserver/WEB-INF/web.xml", geoserver_home.to_string_lossy())
  };

  fs::write(web_xml, r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE web-app PUBLIC "-//Sun Microsystems, Inc.//DTD Web Application 2.3//EN" "http://java.sun.com/dtd/web-app_2_3.dtd">
<web-app>
    <display-name>GeoServer</display-name>
  
      <context-param>
    <param-name>serviceStrategy</param-name>
    <!-- Meaning of the different values :
         
         PARTIAL-BUFFER2
         - Partially buffers the first xKb to disk. Once that has buffered, the the 
           result is streamed to the user. This will allow for most errors to be caught
           early. 
           
         BUFFER
         - stores the entire response in memory first, before sending it off to
           the user (may run out of memory)

         SPEED
         - outputs directly to the response (and cannot recover in the case of an
           error)

         FILE
         - outputs to the local filesystem first, before sending it off to the user
      -->
    <param-value>PARTIAL-BUFFER2</param-value>
  </context-param>
  
  <context-param>
    <!-- see comments on the PARTIAL-BUFFER strategy -->
    <!-- this sets the size of the buffer.  default is "50" = 50kb -->

    <param-name>PARTIAL_BUFFER_STRATEGY_SIZE</param-name>
    <param-value>50</param-value>
  </context-param>
  
  <!--Can be true or false (defaults to: false). -->
  <!--When true the JSONP (text/javascript) output format is enabled -->
  <!--
  <context-param>
    <param-name>ENABLE_JSONP</param-name>
    <param-value>true</param-value>
  </context-param>
  -->
    <!-- 
    <context-param>
      <param-name>PROXY_BASE_URL</param-name>
      <param-value>http://82.58.146.45/geoserver</param-value>
    </context-param>
     -->
   
     <!--
    <context-param>
       <param-name>GEOSERVER_DATA_DIR</param-name>
        <param-value>C:\eclipse\workspace\geoserver_trunk\cite\confCiteWFSPostGIS</param-value>
    </context-param> 
   -->
    
    <!-- pick up all spring application contexts -->
    <context-param>
        <param-name>contextConfigLocation</param-name>
        <param-value>classpath*:/applicationContext.xml classpath*:/applicationSecurityContext.xml</param-value>
    </context-param>
    
    <filter>
     <filter-name>FlushSafeFilter</filter-name>
     <filter-class>org.geoserver.filters.FlushSafeFilter</filter-class>
    </filter>
     
    <filter>
      <filter-name>Set Character Encoding</filter-name>
      <filter-class>org.springframework.web.filter.CharacterEncodingFilter</filter-class>
      <init-param>
        <param-name>encoding</param-name>
        <param-value>UTF-8</param-value>
      </init-param>
    </filter>

    <filter>
     <filter-name>SessionDebugger</filter-name>
     <filter-class>org.geoserver.filters.SessionDebugFilter</filter-class>
    </filter>

    <filter>
    <filter-name>filterChainProxy</filter-name>     
     <filter-class> org.springframework.web.filter.DelegatingFilterProxy</filter-class>
    </filter>

    <filter>
      <filter-name>xFrameOptionsFilter</filter-name>
      <filter-class>org.geoserver.filters.XFrameOptionsFilter</filter-class>
    </filter>

   <filter>
     <filter-name>GZIP Compression Filter</filter-name>
     <filter-class>org.geoserver.filters.GZIPFilter</filter-class>
     <init-param>
         <!-- The compressed-types parameter is a comma-separated list of regular expressions.
              If a mime type matches any of the regular expressions then it will be compressed.
              -->
         <param-name>compressed-types</param-name>
         <param-value>text/.*,.*xml.*,application/json,application/x-javascript</param-value>
     </init-param>
   </filter>

   <filter>
     <filter-name>Request Logging Filter</filter-name>
     <filter-class>org.geoserver.filters.LoggingFilter</filter-class>
     <init-param>
         <!-- The 'enabled' parameter is a boolean value, "true" (case-insensitive) for true or
              any other value for false.  If enabled, then the logging will be performed;
              otherwise the logging filter will have no effect.  If not specified, this 
              parameter defaults to false.
              -->
         <param-name>enabled</param-name>
         <param-value>false</param-value>
     </init-param>
     <init-param>
         <!-- The 'log-request-headers' parameter is a boolean value, "true" (case-insensitive) for
              true or any other value for false.  If enabled, then the logging will include the HTTP 
              headers of requests.  If not specified, this parameter defaults to false.
              -->
         <param-name>log-request-headers</param-name>
         <param-value>false</param-value>
     </init-param>  
     <init-param>
     <!-- The 'log-request-bodies' parameter is a boolean value, "true" (case-insensitive) for
          true or any other value for false.  If enabled, then the logging will include the body
          of POST and PUT requests.  If not specified, this parameter defaults to false.
          Note that this may noticeably degrade responsiveness of your geoserver since it will
          not begin to process requests until the entire request body has been received by the 
          server.
          -->
     <param-name>log-request-bodies</param-name>
     <param-value>false</param-value>
     </init-param>
   </filter>
   
   <filter>
     <filter-name>Advanced Dispatch Filter</filter-name>
     <filter-class>org.geoserver.platform.AdvancedDispatchFilter</filter-class>
     <!-- 
     This filter allows for a single mapping to the spring dispatcher. However using /* as a mapping
     in a servlet mapping causes the servlet path to be "/" of the request. This causes problems with
     library like wicket and restlet. So this filter fakes the servlet path by assuming the first 
     component of the path is the mapped path. 
     -->
   </filter>
   
   <filter>
    <filter-name>Spring Delegating Filter</filter-name>
    <filter-class>org.geoserver.filters.SpringDelegatingFilter</filter-class>
    <!--
    This filter allows for filters to be loaded via spring rather than 
    registered here in web.xml.  One thing to note is that for such filters 
    init() is not called. INstead any initialization is performed via spring 
    ioc.
    -->
   </filter>
   
   <filter>
     <filter-name>Thread locals cleanup filter</filter-name>
     <filter-class>org.geoserver.filters.ThreadLocalsCleanupFilter</filter-class>
     <!-- 
     This filter cleans up thread locals Geotools is setting up for concurrency and performance
     reasons 
     -->
   </filter>

   <!-- Uncomment following filter to enable CORS in Jetty. Do not forget the second config block further down. -->
    <filter>
      <filter-name>cross-origin</filter-name>
      <filter-class>org.eclipse.jetty.servlets.CrossOriginFilter</filter-class>
      <init-param>
        <param-name>chainPreflight</param-name>
        <param-value>false</param-value>
      </init-param>
      <init-param>
        <param-name>allowedOrigins</param-name>
        <param-value>*</param-value>
      </init-param>
      <init-param>
        <param-name>allowedMethods</param-name>
        <param-value>GET,POST,PUT,DELETE,HEAD,OPTIONS</param-value>
      </init-param>
      <init-param>
        <param-name>allowedHeaders</param-name>
        <param-value>*</param-value>
      </init-param>
    </filter>
    
   <!-- Uncomment following filter to enable CORS in Tomcat. Do not forget the second config block further down.
    <filter>
      <filter-name>cross-origin</filter-name>
      <filter-class>org.apache.catalina.filters.CorsFilter</filter-class>
      <init-param>
        <param-name>cors.allowed.origins</param-name>
        <param-value>*</param-value>
      </init-param>
      <init-param>
        <param-name>cors.allowed.methods</param-name>
        <param-value>GET,POST,PUT,DELETE,HEAD,OPTIONS</param-value>
      </init-param>
      <init-param>
        <param-name>cors.allowed.headers</param-name>
        <param-value>*</param-value>
      </init-param>
    </filter>
    -->

    <!-- 
      THIS FILTER MAPPING MUST BE THE FIRST ONE, otherwise we end up with ruined chars in the input from the GUI
      See the "Note" in the Tomcat character encoding guide:
      http://wiki.apache.org/tomcat/FAQ/CharacterEncoding
    -->
    <filter-mapping>
      <filter-name>Set Character Encoding</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
   
   <!-- Uncomment following filter to enable CORS -->
    <filter-mapping>
        <filter-name>cross-origin</filter-name>
        <url-pattern>/*</url-pattern>
    </filter-mapping>
   
    <filter-mapping>
      <filter-name>FlushSafeFilter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <filter-mapping>
      <filter-name>SessionDebugger</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>

    <filter-mapping>
      <filter-name>GZIP Compression Filter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>

    <filter-mapping>
      <filter-name>xFrameOptionsFilter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <filter-mapping>
      <filter-name>Request Logging Filter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
   
    <!-- 
      If you want to use your security system comment out this one too
    -->
    <filter-mapping>
      <filter-name>filterChainProxy</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <filter-mapping>
      <filter-name>Advanced Dispatch Filter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>

    <filter-mapping>
      <filter-name>Spring Delegating Filter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <filter-mapping>
      <filter-name>Thread locals cleanup filter</filter-name>
      <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <!-- general initializer, should be first thing to execute -->
    <listener>
      <listener-class>org.geoserver.GeoserverInitStartupListener</listener-class>
    </listener>
    
    <!-- logging initializer, should execute before spring context startup -->
    <listener>
      <listener-class>org.geoserver.logging.LoggingStartupContextListener</listener-class>
    </listener>
  
    <!--  spring context loader -->
    <listener>
      <listener-class>org.geoserver.platform.GeoServerContextLoaderListener</listener-class>
    </listener>
    
    <!--  http session listener proxy -->
    <listener>
      <listener-class>org.geoserver.platform.GeoServerHttpSessionListenerProxy</listener-class>
    </listener>

  <!-- request context listener for session-scoped beans -->
  <listener>
    <listener-class>org.springframework.web.context.request.RequestContextListener</listener-class>
  </listener>
    
    <!-- spring dispatcher servlet, dispatches all incoming requests -->
    <servlet>
      <servlet-name>dispatcher</servlet-name>
      <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
    </servlet>
    
    <!-- single mapping to spring, this only works properly if the advanced dispatch filter is 
         active -->
    <servlet-mapping>
        <servlet-name>dispatcher</servlet-name>
        <url-pattern>/*</url-pattern>
    </servlet-mapping>
    
    <mime-mapping>
      <extension>xsl</extension>
      <mime-type>text/xml</mime-type>
    </mime-mapping>
    <mime-mapping>
      <extension>sld</extension>
      <mime-type>text/xml</mime-type>
    </mime-mapping>
    <mime-mapping>
      <extension>json</extension>
      <mime-type>application/json</mime-type>
    </mime-mapping>
  
    <welcome-file-list>
        <welcome-file>index.html</welcome-file>
    </welcome-file-list>
    
</web-app>
  "#
  )?;


  let log4j_props = if cfg!(windows) {
    format!("{}\\log4j.properties", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/log4j.properties", geoserver_home.to_string_lossy())
  };

  // Write our config for geoserver...
  fs::write(log4j_props, r#"

## Log4J Level          java.util.logging Level
## --------------------------------------------
## ALL                   FINEST
## TRACE                 FINER
## DEBUG                 FINE (includes CONFIG)
## INFO                  INFO
## ERROR/ERROR           ERRORING
## ERROR                 SEVERE
## OFF                   OFF

log4j.rootLogger=OFF, stdout

log4j.appender.stdout=org.apache.log4j.ConsoleAppender
log4j.appender.stdout.layout=org.apache.log4j.PatternLayout
log4j.appender.stdout.layout.ConversionPattern=%-4r [%t] %-5p %c %x - %m%n

"#)?;

  // We also overwrite the startup scripts.
  // By default these run "start.jar" which forks a process
  // that persists after we exit. To prevent this we use the "--dry-run" flag
  // and capture the command to be run.
  // We then run _that_ process directly, which does not fork.
  // This ensures we can kill our children cleanly instead of having
  // to resort to parsing "ps -aux" or "wmic process", which is phenomenally unreliable.

  let startup_bat = if cfg!(windows) {
    format!("{}\\startup.bat", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/startup.bat", geoserver_home.to_string_lossy())
  };

  fs::write(startup_bat, r#"@echo off
rem -----------------------------------------------------------------------------
rem Startup Script for GeoServer
rem -----------------------------------------------------------------------------

cls
echo Welcome to GeoServer!
echo.
set error=0

rem JAVA_HOME not defined
if "%JAVA_HOME%" == "" goto trySystemJava

rem JAVA_HOME defined incorrectly
if not exist "%JAVA_HOME%\bin\java.exe" goto badJava

rem Setup the java command and move on
set RUN_JAVA=%JAVA_HOME%\bin\java
echo JAVA_HOME: %JAVA_HOME%
echo.

:checkGeoServerHome
rem GEOSERVER_HOME not defined
if "%GEOSERVER_HOME%" == "" goto noHome

rem GEOSERVER_HOME defined incorrectly
if not exist "%GEOSERVER_HOME%\bin\startup.bat" goto badHome

goto checkDataDir

:trySystemJava
  echo The JAVA_HOME environment variable is not defined, trying to use System Java
for /f "tokens=*" %%i in ('where java') do set RUN_JAVA=%%i
rem --- we might be on amd64 having only x86 jre installed ---
if "%RUN_JAVA%"=="" if DEFINED ProgramFiles(x86) if NOT "%PROCESSOR_ARCHITECTURE%"=="x86" (
    rem --- restart the batch in x86 mode---
    echo Warning: No java interpreter found in path.
    echo Retry using Wow64 filesystem [32bit environment] redirection.
    %SystemRoot%\SysWOW64\cmd.exe /c %0 %*
    exit /b %ERRORLEVEL%
  )
if "%RUN_JAVA%"=="" goto noJava
  echo Using System Java at:
  echo    %RUN_JAVA%
  echo.
goto checkGeoServerHome

:noJava
  echo The JAVA_HOME environment variable is not defined, and no Java executable could be found.
goto JavaFail

:badJava
  echo The JAVA_HOME environment variable is not defined correctly.
goto JavaFail

:JavaFail
  echo Please install Java or, if present but not in the path, set this environment variable via the following command:
  echo    set JAVA_HOME=[path to Java]
  echo Example:
  echo    set JAVA_HOME=C:\Program Files\Java\jdk8
  echo.
  set error=1
goto end

:noHome
  if exist ..\start.jar goto noHomeOK
  echo The GEOSERVER_HOME environment variable is not defined.
goto HomeFail

:badHome
  if exist ..\start.jar goto badHomeOK
  echo The GEOSERVER_HOME environment variable is not defined correctly.
goto HomeFail

:HomeFail
  echo This environment variable is needed to run this program.
  echo.
  echo Set this environment variable via the following command:
  echo    set GEOSERVER_HOME=[path to GeoServer]
  echo Example:
  echo    set GEOSERVER_HOME=C:\Program Files\GeoServer
  echo.
  set error=1
goto end


:noHomeOK
  echo The GEOSERVER_HOME environment variable is not defined.
goto setHome

:badHomeOK
  echo The GEOSERVER_HOME environment variable is not defined correctly.
goto setHome

:setHome
  echo Temporarily setting GEOSERVER_HOME to the following directory:
  cd ..
  set GEOSERVER_HOME=%CD%
  echo %GEOSERVER_HOME%
  echo.
goto checkDataDir


:checkDataDir
  rem GEOSERVER_DATA_DIR not defined
  if "%GEOSERVER_DATA_DIR%" == "" goto noDataDir
  goto setMarlinRenderer

:noDataDir
  rem if GEOSERVER_DATA_DIR is not defined then use GEOSERVER_HOME/data_dir/
  if exist "%GEOSERVER_HOME%\data_dir" goto setDataDir
  echo No valid GeoServer data directory could be located.
  echo Please set the GEOSERVER_DATA_DIR environment variable.
  echo.
  echo Set this environment variable via the following command:
  echo    set GEOSERVER_DATA_DIR=[path to data_dir]
  echo Example:
  echo    set GEOSERVER_DATA_DIR=C:\Program Files\GeoServer\data_dir
  echo.
  set error=1
goto end

:setDataDir
  set GEOSERVER_DATA_DIR=%GEOSERVER_HOME%\data_dir
  echo The GEOSERVER_DATA_DIR environment variable is not defined correctly.
  echo Temporarily setting GEOSERVER_DATA_DIR to the following directory:
  echo %GEOSERVER_DATA_DIR%
  echo.
goto setMarlinRenderer

:setMarlinRenderer
  cd "%GEOSERVER_HOME%"
  for /f "delims=" %%i in ('dir /b/s "%GEOSERVER_HOME%\webapps\geoserver\WEB-INF\lib\marlin*.jar"') do set MARLIN_JAR=%%i
  if "%MARLIN_JAR%" == "" (
    echo Marlin renderer jar not found
    goto run
  )
  set MARLIN_ENABLER=-Xbootclasspath/a:"%MARLIN_JAR%" -Dsun.java2d.renderer=org.marlin.pisces.MarlinRenderingEngine
  set JAVA_OPTS=%JAVA_OPTS% %MARLIN_ENABLER%
goto run

:run
  cd "%GEOSERVER_HOME%"
  echo Please wait while loading GeoServer...
  echo.
  "%RUN_JAVA%" %JAVA_OPTS% -DGEOSERVER_DATA_DIR="%GEOSERVER_DATA_DIR%" -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar --dry-run
  cd bin
goto end


:end
  if %error% == 1 echo Startup of GeoServer was unsuccessful. 
  echo.
  pause

  "#)?;



  let startup_sh = if cfg!(windows) {
    format!("{}\\startup.sh", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/startup.sh", geoserver_home.to_string_lossy())
  };

  fs::write(startup_sh, r#"#!/bin/sh
# -----------------------------------------------------------------------------
# Start Script for GEOSERVER
#
# $Id$
# -----------------------------------------------------------------------------

# Guard against misconfigured JAVA_HOME
if [ ! -z "$JAVA_HOME" -a ! -x "$JAVA_HOME"/bin/java ]; then
  echo "The JAVA_HOME environment variable is set but JAVA_HOME/bin/java"
  echo "is missing or not executable:"
  echo "    JAVA_HOME=$JAVA_HOME"
  echo "Please either set JAVA_HOME so that the Java runtime is JAVA_HOME/bin/java"
  echo "or unset JAVA_HOME to use the Java runtime on the PATH."
  exit 1
fi

# Find java from JAVA_HOME or PATH
if [ ! -z "$JAVA_HOME" ]; then
  _RUNJAVA="$JAVA_HOME"/bin/java
elif [ ! -z "$(which java)" ]; then
  _RUNJAVA=java
else
  echo "A Java runtime (java) was not found in JAVA_HOME/bin or on the PATH."
  echo "Please either set the JAVA_HOME environment variable so that the Java runtime"
  echo "is JAVA_HOME/bin/java or add the Java runtime to the PATH."
  exit 1
fi

if [ -z $GEOSERVER_HOME ]; then
  #If GEOSERVER_HOME not set then guess a few locations before giving
  # up and demanding user set it.
  if [ -r start.jar ]; then
     echo "GEOSERVER_HOME environment variable not found, using current "
     echo "directory.  If not set then running this script from other "
     echo "directories will not work in the future."
     export GEOSERVER_HOME=`pwd`
  else 
    if [ -r ../start.jar ]; then
      echo "GEOSERVER_HOME environment variable not found, using current "
      echo "location.  If not set then running this script from other "
      echo "directories will not work in the future."
      export GEOSERVER_HOME=`pwd`/..
    fi
  fi 

  if [ -z "$GEOSERVER_HOME" ]; then
    echo "The GEOSERVER_HOME environment variable is not defined"
    echo "This environment variable is needed to run this program"
    echo "Please set it to the directory where geoserver was installed"
    exit 1
  fi

fi

if [ ! -r "$GEOSERVER_HOME"/bin/startup.sh ]; then
  echo "The GEOSERVER_HOME environment variable is not defined correctly"
  echo "This environment variable is needed to run this program"
  exit 1
fi

#Find the configuration directory: GEOSERVER_DATA_DIR
if [ -z $GEOSERVER_DATA_DIR ]; then
    if [ -r "$GEOSERVER_HOME"/data_dir ]; then
        export GEOSERVER_DATA_DIR="$GEOSERVER_HOME"/data_dir
    else
        echo "No GEOSERVER_DATA_DIR found, using application defaults"
        GEOSERVER_DATA_DIR=""
    fi
fi

cd "$GEOSERVER_HOME"

if [ -z $MARLIN_JAR]; then
    export MARLIN_JAR=`find \`pwd\`/webapps -name "marlin*.jar" | head -1`
    export MARLIN_ENABLER="-Xbootclasspath/a:$MARLIN_JAR -Dsun.java2d.renderer=org.marlin.pisces.MarlinRenderingEngine"
fi

echo "GEOSERVER DATA DIR is $GEOSERVER_DATA_DIR"
#added headless to true by default, if this messes anyone up let the list
#know and we can change it back, but it seems like it won't hurt -ch
exec "$_RUNJAVA" $JAVA_OPTS $MARLIN_ENABLER -DGEOSERVER_DATA_DIR="$GEOSERVER_DATA_DIR" -Djava.awt.headless=true -DSTOP.PORT=8079 -DSTOP.KEY=geoserver -jar start.jar --dry-run

  "#)?;




  // Run startup script and capture geoserver command

  let startup_script = if cfg!(windows) {
    format!("{}\\startup.bat", geoserver_home.to_string_lossy())
  }
  else {
    format!("{}/startup.sh", geoserver_home.to_string_lossy())
  };

  #[cfg(not(windows))]
  {
    // ensure startup script is executable
    ensure_file_is_executable(&startup_script);
  }

  eprintln!("Executing: {}", &startup_script);

  let mut geoserver_data_dir = geoserver_home.clone();
  geoserver_data_dir.push("data_dir"); // Default location in unzipped app dir

  let output = Command::new(&startup_script)
                .current_dir(&geoserver_home.to_string_lossy()[..])
                .env("GEOSERVER_HOME", &geoserver_home.to_string_lossy()[..])
                .env("GEOSERVER_DATA_DIR", &geoserver_data_dir.to_string_lossy()[..])
                .output()?;

  let stdout = String::from_utf8_lossy(&output.stdout);
  //let stderr = String::from_utf8_lossy(&output.stderr);

  //println!("geoserver stdout={}", stdout);
  //println!("geoserver stderr={}", stderr);

  // Grab first stdout line containing the word "java" that is >80 characters long.
  // This heuristic may need to be updated in the future.
  let mut geoserver_cmd_s = String::new();
  for line in stdout.lines() {
    if line.contains("java") && line.len() > 80 {
      geoserver_cmd_s = line.to_string();
    }
  }

  // Double-escape b/c shlex::split removes '\C' chars.
  // We must keep '\ ' lines however!
  let re = regex::Regex::new(r"\\(?P<c>[a-zA-Z0-9_])").unwrap();
  let geoserver_cmd_s = re.replace_all(&geoserver_cmd_s, "\\\\$c");

  println!("geoserver_cmd_s={}", &geoserver_cmd_s[..]);

  // Parse stdout as a command + execute that to have a non-forking geoserver process
  if let Some(split) = shlex::split(&geoserver_cmd_s[..]) {
    
    println!("split={:?}", &split);

    if split.len() < 2 {
      // Something broke, return a dummy command.
      panic!("// TODO debug geoserver_cmd_s not having >1 tokens");
    }

    let mut java_exe_path: String = split[0].to_string();

    if cfg!(target_os = "windows") {
      if java_exe_path.contains("java.exe") {
        // Use the java wrapper to prevent CLI GUI from opening
        java_exe_path = java_exe_path.replace("java.exe", "javaw.exe");
      }
    }

    return Ok((
      startup_script.to_owned(),
      Command::new(&java_exe_path[..])
        .current_dir(&geoserver_home.to_string_lossy()[..])
        .env("GEOSERVER_HOME", &geoserver_home.to_string_lossy()[..])
        .env("GEOSERVER_DATA_DIR", &geoserver_data_dir.to_string_lossy()[..])
        .args(&split[1..])
        // The geoserver stdout/stderr is not important to us
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()?
    ));

  }
  
  panic!("Could not split geoserver command from stdout")

}

