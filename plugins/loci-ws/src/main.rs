/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use loci;

use actix::{Actor, StreamHandler};
use actix_web::{web, App, Error, HttpRequest, HttpResponse, HttpServer};
use actix_web_actors::ws;
use actix_rt;

use rust_embed::RustEmbed;

use std::sync::atomic::AtomicBool;
use std::sync::{Arc};

const HTTP_PORT: u64 = 8080;
const APP_NAME: &'static str = "loci";

#[derive(RustEmbed)]
#[folder = "src/www"]
struct WWWAssets;

/// Define HTTP actor
struct MyWs;

impl Actor for MyWs {
    type Context = ws::WebsocketContext<Self>;
}

/// Handler for ws::Message message
impl StreamHandler<Result<ws::Message, ws::ProtocolError>> for MyWs {
    fn handle(
        &mut self,
        msg: Result<ws::Message, ws::ProtocolError>,
        ctx: &mut Self::Context,
    ) {
        match msg {
            Ok(ws::Message::Ping(msg)) => ctx.pong(&msg),
            Ok(ws::Message::Text(text)) => handle_ws_txt(text, self, ctx),
            //Ok(ws::Message::Binary(bin)) => ctx.binary(bin),
            Ok(ws::Message::Binary(_bin)) => (),
            _ => (),
        }
    }
}

fn json_unwrap_s(val: &serde_json::Map::<String, serde_json::Value>, key: &str, default: &str) -> String {
  // All this does is grab the value of "key" as a string, or the value of default and claims ownership.
  val.get(key).unwrap_or(&serde_json::Value::String(default.to_string())).as_str().unwrap_or(default).to_string()
}

fn handle_ws_txt(text: String, _ws: &mut MyWs, ctx: &mut ws::WebsocketContext<MyWs>) {
  use serde_json::value::Value;

  match serde_json::from_str::<Value>(&text) {
    Ok(Value::Object(val)) => {
      match &json_unwrap_s(&val, "type", "null")[..] {
        "db-query-constant" => {
          let query_s = json_unwrap_s(&val, "query", "");
          let callback_js_fn = json_unwrap_s(&val, "callback", "console.log");

          // DB queries return a [{"col-a": val-a}, {"col-a": val-a}}], 
          // and as such are not suited for high-volume queries.
          let mut resp = serde_json::json!([]);

          match loci::db::get_init_db_conn() {
            Ok(conn) => {
              match conn.prepare(&query_s[..]) {
                Ok(mut stmt) => {
                  if let Ok(mut rows) = stmt.query(rusqlite::NO_PARAMS) {
                    while let Ok(Some(row)) = rows.next() {
                      let mut resp_i = serde_json::json!({});

                      for i in 0..row.column_count() {
                        if let Ok(column) = row.column_name(i) {
                          
                          // We try to get the val as a string -> int -> real and assign to the JSON map

                          if let Ok(column_val) = row.get(i) {
                            let column_val: String = column_val;
                            resp_i[column] = serde_json::Value::String(column_val);
                          }

                          else if let Ok(column_val) = row.get(i) {
                            let column_val: isize = column_val;
                            resp_i[column] = serde_json::Value::Number(serde_json::Number::from_f64(column_val as f64).expect("Invalid number from SQL to JSON"));
                          }

                          else if let Ok(column_val) = row.get(i) {
                            let column_val: f64 = column_val;
                            resp_i[column] = serde_json::Value::Number(serde_json::Number::from_f64(column_val).expect("Invalid number from SQL to JSON"));
                          }

                          else {
                            println!("WARNING: cannot format data from sql column {} for JSON response!", &column[..]);
                          }


                        }
                      }

                      resp.as_array_mut().unwrap().push(resp_i);

                    }
                  }
                }
                Err(e) => {
                  println!("{}:{}: e={} query_s={}", std::file!(), std::line!(), e, query_s);
                }
              }
              
              ctx.text(
                format!("{}({});", callback_js_fn, &resp)
              );
            }
            Err(e) => {
              println!("{}:{}: DB e={:?}", std::file!(), std::line!(), e);
              ctx.text(format!("DB e={:?}", e));
            }
          }
        }
        unk => {
          println!("Unhandled ws type={} val = {:?}", unk, val);
          ctx.text(format!("Unhandled ws type={} val = {:?}", unk, val));
        }
      }

    }
    Ok(other) => {
      println!("ws unexpected value = {}", other);
      ctx.text(format!("ws unexpected value = {}", other));
    }
    Err(e) => {
      println!("{}:{}: ws e = {}", std::file!(), std::line!(), e);
      ctx.text(format!("ws e = {}", e));
    }
  }
  
}

// This fn upgrades /ws/ http requests to a websocket connection
// which may stream events to/from the GUI
async fn ws_handler(req: HttpRequest, stream: web::Payload) -> Result<HttpResponse, Error> {
    let resp = ws::start(MyWs {}, &req, stream);
    //println!("{:?}", resp);
    resp
}

// This fn grabs assets and returns them
async fn index(req: HttpRequest, _stream: web::Payload) -> HttpResponse {
  
  // We perform some common routing tactics here
  let mut r_path = req.path();
  if r_path == "/" {
    r_path = "index.html";
  }
  else if r_path.starts_with("/") {
    r_path = &r_path[1..];
  }

  // Finally pull from fs/memory 
  match WWWAssets::get(r_path) {
    Some(data) => {
      // Figure out MIME from file extension
      let guess = mime_guess::from_path(r_path);
      let mime_s = guess.first_raw().unwrap_or("application/octet-stream");
      let owned_data: Vec<u8> = (&data[..]).iter().cloned().collect();
      HttpResponse::Ok()
            .content_type(mime_s)
            .body(owned_data)
    }
    None => {
      HttpResponse::NotFound()
        .content_type("text/html")
        .body(&include_bytes!("www/404.html")[..])
    }
  }
}

fn main() {

  let sys = actix_rt::System::new(crate::APP_NAME);
  
  let address = format!("127.0.0.1:{}", crate::HTTP_PORT);

  HttpServer::new(|| {
      // See https://docs.rs/actix-cors/0.5.3/actix_cors/struct.Cors.html#method.permissive
      //let cors = actix_cors::Cors::default();
      let cors = actix_cors::Cors::permissive();

      App::new()
        .wrap(cors)
        .route("/ws", web::get().to(ws_handler))
        //.route("/", web::get().to(index))
        .default_service(
          web::route().to(index)
        )
    })
    .bind(&address)
    .unwrap()
    .run();

  let _ = sys.run();
}
