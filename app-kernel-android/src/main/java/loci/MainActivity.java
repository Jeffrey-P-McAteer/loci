package loci;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebChromeClient;
import android.webkit.ConsoleMessage;
import android.provider.Settings.Secure;

import java.io.*;
import java.util.*;


/**
 * For protected methods see https://developer.android.com/reference/android/app/Activity
 */
public class MainActivity extends Activity {

    private String[] subprogram_envp = null;

    // "you perform basic application startup logic that should happen only once for the entire life of the activity"
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        initialize_subprogram_envp();
        write_device_id_to_app_root_file();
        spawn_threads(
          this::run_webserver_t
        );
        try {
          Thread.sleep(250);
        }
        catch (Exception e) { e.printStackTrace(); }
        setContentView(R.layout.activity_main);
    }

    // Runs every time app is focused
    protected void onStart() {
      super.onStart();
      WebView wv = (WebView) findViewById(R.id.webview);
      wv.getSettings().setJavaScriptEnabled(true);
      wv.setWebChromeClient(new WebChromeClient() {
        @Override public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
          System.err.println("app_kernel JS console> "+consoleMessage.sourceId()+":"+consoleMessage.lineNumber()+": "+consoleMessage.message());
          return super.onConsoleMessage(consoleMessage);
        }
      });
      wv.loadUrl("http://127.0.0.1:7010/");
    }

    private void run_webserver_t() {
        supervise_long_process("server_webgui", () -> System.err.println("Restarting server_webgui"));
    }

    private void initialize_subprogram_envp() {
        final ArrayList<String> env = new ArrayList<>();
        for (Map.Entry<String, String> entry : System.getenv().entrySet()) {
          env.add(String.format("%s=%s", entry.getKey(), entry.getValue()));
        }
        // Add our own, read by subprograms and app-lib
        // See app-kernel/src/main.rs set_env_vars() and keep in sync.
        env.add(String.format("LOCI_DATA_DIR=%s", this.getDataDir().getAbsolutePath()));
        env.add(String.format("LOCI_INSTALL_DIR=%s", this.getDataDir().getAbsolutePath()));

        this.subprogram_envp = new String[env.size()];
        for (int i=0; i<this.subprogram_envp.length; i++) {
          this.subprogram_envp[i] = env.get(i);
        }
    }

    private void write_device_id_to_app_root_file() {
        File id_file = new File(this.getDataDir(), "machine_id.txt");
        String machine_id = Secure.getString(this.getContentResolver(), Secure.ANDROID_ID);
        try {
          try (PrintWriter out = new PrintWriter(id_file)) {
            out.println(machine_id);
          }
        }
        catch (Exception e) { e.printStackTrace(); }
    }

    private void spawn_threads(Runnable... tasks) {
      Thread[] threads = new Thread[tasks.length];
      for (int i=0; i<tasks.length; i++) {
        threads[i] = new Thread(tasks[i]);
        threads[i].start();
      }
    }

    private void supervise_long_process(String exe_name, Runnable on_stop) {
      File exe_f = extract_raw_resource(exe_name);
      try {
        Runtime.getRuntime().exec(new String[]{ // Make binary executable
          "/system/bin/chmod", "744", exe_f.getAbsolutePath()
        });
      }
      catch (Exception e) { e.printStackTrace(); }
      Process process = null;
      while (true) {
        // Kill old children
        if (process != null) {
          try { process.destroyForcibly(); }
          catch (Exception e) { e.printStackTrace(); }
        }
        // Spawn child
        try {
          process = Runtime.getRuntime().exec(new String[]{
            exe_f.getAbsolutePath()
          }, this.subprogram_envp);
        }
        catch (Exception e) { e.printStackTrace(); }
        // Block until exit
        while (process != null && process.isAlive()) {
          try { Thread.sleep(250); }
          catch (Exception e) { e.printStackTrace(); }
        }
        try { Thread.sleep(250); }
        catch (Exception e) { e.printStackTrace(); }
      }
    }

    private File extract_raw_resource(String filename) {
      File exe_file = null;
      try {
          InputStream input = this.getResources().openRawResource(
            this.getResources().getIdentifier(filename, "raw", this.getPackageName())
          );

          exe_file = new File(this.getDataDir(), filename);

          byte[] buffer = new byte[16000];
          int read;
          try (OutputStream output = new FileOutputStream(exe_file)) {
            while ((read = input.read(buffer)) != -1) {
              output.write(buffer, 0, read);
            }
          }

          input.close();

          return exe_file;
        }
        catch (Exception e) {
          e.printStackTrace();
          return exe_file;
        }
    }

}

