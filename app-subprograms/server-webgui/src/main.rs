
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
use std::str::FromStr;

#[derive(RustEmbed)]
#[folder = "www"]
struct WWWData;

#[cfg(not(tarpaulin_include))]
#[tokio::main(worker_threads = 2)]
async fn main() {

    let routes = warp::path("ws")
        .and(warp::ws()) // The `ws()` filter will prepare the Websocket handshake.
        .map(|ws: Ws| {
            ws.on_upgrade(|websocket| { // When the client upgrades, forward to websocket_handler for business logic
                let (tx, rx) = websocket.split();
                websocket_handler(tx, rx)
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
        .or(warp_embed::embed(&WWWData))
        // If not in www/ try to use a directory set by developers in the LOCI_WWW_FALLBACK environment variable
        .or(warp::fs::dir( env::var("LOCI_WWW_FALLBACK").unwrap_or("/dev/null".to_string()) ));

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

async fn websocket_handler(mut tx: SplitSink<WebSocket, Message>, mut rx: SplitStream<WebSocket>) {
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





