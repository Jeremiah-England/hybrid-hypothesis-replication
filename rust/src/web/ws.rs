use std::sync::Arc;
use actix::{Actor, StreamHandler, AsyncContext};
use actix_web_actors::ws;
use actix_web::{web, Error, HttpRequest, HttpResponse};
use crate::simulation::Simulation;
use serde_json::json;

pub struct SimulationWebSocket {
    simulation: Arc<Simulation>,
}

impl SimulationWebSocket {
    pub fn new(simulation: Arc<Simulation>) -> Self {
        Self { simulation }
    }
}

impl Actor for SimulationWebSocket {
    type Context = ws::WebsocketContext<Self>;
}

impl StreamHandler<Result<ws::Message, ws::ProtocolError>> for SimulationWebSocket {
    fn handle(&mut self, msg: Result<ws::Message, ws::ProtocolError>, ctx: &mut Self::Context) {
        match msg {
            Ok(ws::Message::Ping(msg)) => ctx.pong(&msg),
            Ok(ws::Message::Text(text)) => {
                if text == "start_simulation" {
                    // Run the comparison
                    let (genome1_match, genome2_match, genome3_match) = self.simulation.run_comparison();
                    self.simulation.update_state(genome1_match, genome2_match, genome3_match);
                    let state = self.simulation.get_state();

                    // Prepare the results for sending
                    let response = json!({
                        "type": "simulation_results",
                        "state": state,
                    });
                    
                    // Send the results back to the client
                    ctx.text(serde_json::to_string(&response).unwrap());
                }
            }
            _ => (),
        }
    }
}

pub async fn simulation_websocket(
    req: HttpRequest,
    stream: web::Payload,
    data: web::Data<Arc<Simulation>>,
) -> Result<HttpResponse, Error> {
    let simulation = data.get_ref().clone();
    ws::start(SimulationWebSocket::new(simulation), &req, stream)
}