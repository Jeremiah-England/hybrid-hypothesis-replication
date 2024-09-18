mod genome_comparison;
mod simulation;
mod web;

use actix_web::{App, HttpServer, web as aw_web, HttpResponse};
use aw_web::Data;
use simulation::{Simulation, SimulationConfig};
use std::sync::Arc;
use env_logger;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    log::info!("Hello world!");

    let config = SimulationConfig {
        chunk_size: 42,
        max_differences: 5,
        num_processes: 4,
        update_interval: 100,
        human_genome_path: "../uploads/human_hg38.fa".to_string(),
        genome1_path: "../uploads/bonobo_contigs.fa".to_string(),
        // genome2_path: "../uploads/pig_sscrofa11.1.fa".to_string(),
        genome2_path: "../uploads/bosTau9.fa".to_string(),
        genome3_path: "".to_string(),
        genome1_name: "Bonobo".to_string(),
        genome2_name: "Cow".to_string(),
        genome3_name: "Genome3".to_string(),
    };

    let simulation = Data::new(Arc::new(Simulation::new(config)));

    log::info!("Starting server at http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(simulation.clone())
            .configure(web::routes::config)
            .route("/ws", aw_web::get().to(web::ws::simulation_websocket))
            .service(web::routes::index)  // Add this line
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}

async fn index() -> HttpResponse {
    HttpResponse::Ok().body("Welcome to the Simulation Server!")
}