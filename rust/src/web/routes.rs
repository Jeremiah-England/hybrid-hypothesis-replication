use actix_web::{get, post, web, HttpResponse, Responder};
use serde_json::json;

use crate::simulation::{Simulation, SimulationConfig};

#[get("/")]
async fn index() -> impl Responder {
    HttpResponse::Ok().content_type("text/html").body(include_str!("../../static/index.html"))
}

#[post("/configure")]
async fn configure(
    data: web::Data<Simulation>,
    // config: web::Json<SimulationConfig>
) -> impl Responder {
    // let new_simulation = data.update_config(config.into_inner());
    HttpResponse::Ok().json(json!({
        "message": "Configuration updated successfully",
        "config": data.get_config()
    }))
}

#[get("/state")]
async fn get_state(data: web::Data<Simulation>) -> impl Responder {
    let state = data.get_state();
    HttpResponse::Ok().json(state)
}

pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api")
            .service(index)
            .service(configure)
            .service(get_state)
    );
}