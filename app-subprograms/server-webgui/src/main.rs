
use futures::{FutureExt, StreamExt, SinkExt};
use futures::stream::{SplitSink,SplitStream};

use warp::Filter;
use warp::filters::ws::{WebSocket,Message};
use warp::ws::{Ws,};

use rust_embed::RustEmbed;

use std::env;
use std::collections::HashMap;
use std::path::Path;
use std::net::IpAddr;
use std::net::SocketAddr;
use std::str::FromStr;

use std::sync::atomic::{Ordering,AtomicBool};


#[derive(RustEmbed)]
#[folder = "www"]
struct WWWData;

// Globals
static exit_flag: AtomicBool = AtomicBool::new(false);

#[cfg(not(tarpaulin_include))]
#[tokio::main(worker_threads = 2)]
async fn main() {
    exit_flag.store(false, Ordering::Relaxed);

    std::thread::spawn(|| { db_poll_t(); });

    let routes = warp::path("ws")
        .and(warp::ws()) // The `ws()` filter will prepare the Websocket handshake.
        .and(warp::addr::remote()) // This gives us IP information about the client
        .map(|ws: Ws, remote_addr: Option<SocketAddr>| {
            ws.on_upgrade(move |websocket| { // When the client upgrades, forward to websocket_handler for business logic
                let (tx, rx) = websocket.split();
                websocket_handler(remote_addr, tx, rx)
            })
        })
        // If not /ws serve a function providing a REST API
        .or(
            warp::path("api") // Handles all URLS under /api/ and extracts as much connection data as possible
                .and(warp::filters::path::param::<String>())
                .and(warp::filters::method::method())
                .and(warp::filters::header::headers_cloned())
                .and(warp::filters::body::form())
                .and(warp::filters::addr::remote())
                .map(api_handler)
        )
        // Allow devs to override embedded www/ data at runtime
        .or(warp::fs::dir( env::var("LOCI_WWW_OVERRIDE").unwrap_or("/dev/null".to_string()) ))
        // If not /ws serve embedded www/ directory
        .or(warp_embed::embed(&WWWData));

    // First async worker is HTTP, works everywhere
    let w1 = warp::serve(routes.clone()).run((IpAddr::from_str("::0").expect("Ipv6 is broken!"), 7010));

    // Second async worker is HTTPS, only works when env vars point to existing files:
    
    if let (Ok(ssl_cert_path), Ok(ssl_key_path)) = (env::var("LOCI_SSL_CERT"), env::var("LOCI_SSL_KEY")) {
        if Path::new(&ssl_cert_path).exists() && Path::new(&ssl_key_path).exists() {
            let w2 = warp::serve(routes.clone())
                .tls()
                .cert_path(&ssl_cert_path)
                .key_path(&ssl_key_path)
                .run((IpAddr::from_str("::0").expect("Ipv6 is broken!"), 7011));

            futures::join!(w1, w2);
            return;
        }
    }
    
    // No SSL, await w1 only
    futures::join!(w1);

}

fn api_handler(
    api_path: String,
    method: warp::http::method::Method,
    headers: warp::http::header::HeaderMap,
    body: HashMap<String, String>,
    remote_ip: Option<std::net::SocketAddr>
//) -> warp::http::Result<warp::http::Response<()>> {
) -> warp::reply::Response {

    eprintln!("api_handler api_path={:#?} method={:#?} headers={:#?} body={:#?} remote_ip={:#?}", api_path, method, headers, body, remote_ip);
    
    let mut builder = warp::http::Response::builder()
        .header("X-LOCI", "true")
        .status(warp::http::StatusCode::OK);

    let mut body = warp::hyper::body::Body::empty();

    builder.body(body).expect("Could not build api_handler body")
}

async fn websocket_handler(remote_addr: Option<SocketAddr>, mut tx: SplitSink<WebSocket, Message>, mut rx: SplitStream<WebSocket>) {
    // On connect register in ip_addr_and_nonce in sessions table and store reference to tx
    // in a global variable
    println!("TODO handle remote_addr={:#?}", remote_addr);


    let mut max_empty_msgs = 900;
    loop {
        match rx.next().await {
            Some(result) => {
                match result {
                    Ok(msg) => {
                        if let Ok(msg_str) = msg.to_str() {
                            if let Err(e) = on_ws_msg(msg_str, &mut tx).await {
                                eprintln!("[ websocket_handler ] on_ws_msg returned error: {:#?}", msg);
                            }
                        }
                        else {
                            eprintln!("[ websocket_handler ] Non-text message: {:#?}", msg);
                        }
                    }
                    Err(e) => {
                        eprintln!("[ websocket_handler ] match result e={:#?}", e);
                    }
                }
            }
            None => {
                //eprintln!("[ websocket_handler ] rx.next() == None ");
                max_empty_msgs -= 1;
            }
        }
        if max_empty_msgs < 1 {
            break;
        }
    }
}

async fn on_ws_msg<'a>(msg_txt: &str, tx: &'a mut SplitSink<WebSocket, Message>) -> Result<(), Box<dyn std::error::Error>> {
    println!("on_ws_msg({})", msg_txt);
    
    tx.send(Message::text(msg_txt)).await?;

    let msg = serde_json::from_str(msg_txt)?;
    
    Ok(())
}

/**
 * Exits when >400 errors occur in db_poll_t_e OR exit_flag is set to true.
 */
fn db_poll_t() {
    let mut max_failures = 400;
    loop {
        if max_failures < 1 {
            break;
        }
        if let Err(e) = db_poll_t_e() {
            eprintln!("server-webgui {}:{} {}", file!(), line!(), e);
            max_failures -= 1;
            std::thread::sleep(std::time::Duration::from_millis(500));
        }

        if exit_flag.load(Ordering::Relaxed) {
          break;
        }
    }
}

fn db_poll_t_e() -> Result<(), Box<dyn std::error::Error>> {
    let mut gui_db = app_lib::open_app_db("gui")?; // see gui.sql
    loop {
        std::thread::sleep(std::time::Duration::from_millis(350));
        
        if exit_flag.load(Ordering::Relaxed) {
          break;
        }

        // for all rows in js_push table...
        let mut stmt = gui_db.prepare(
            "SELECT js_push.rowid, js_push.client_js, sessions.ip_addr_and_nonce FROM js_push JOIN sessions ON js_push.session_id = sessions.rowid"
        )?;
        let mut rows = stmt.query([])?;
        
        let mut processed_row_ids: Vec<isize> = vec![];

        while let Some(row) = rows.next()? {
            let js_push_rowid: isize = row.get(0)?;
            let client_js: String = row.get(1)?;
            let ip_addr_and_nonce: String = row.get(2)?;
            
            println!("TODO client_js={}   ip_addr_and_nonce={}", client_js, ip_addr_and_nonce);

            processed_row_ids.push(js_push_rowid);

        }

        if processed_row_ids.len() > 0 {
            let sql = format!("DELETE FROM js_push WHERE rowid NOT IN ({})", app_lib::util_repeat_sql_vars(processed_row_ids.len()) );
            let parameters = app_lib::rusqlite::params_from_iter(processed_row_ids.iter());
            gui_db.execute(&sql, parameters)?;
        }

    }

    Ok(())
}



