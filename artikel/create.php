<?php

/**********************/
/* Create new article */
/**********************/

// required headers
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

// include database and object files
include_once '../config/database.php';
include_once '../objects/artikel.php';

// instantiate database and artikel object
$database = new Database();
$db = $database->getConnection();

// initialize object
$artikel = new Artikel($db);

// read parameters from POST method
$lieferant_id = $_POST['lieferant_id'];
$artikel_nr = isset($_POST['artikel_nr']) ? $_POST['artikel_nr'] : null;

if (is_null($lieferant_id)) {
  // set response code - 400 bad request
  http_response_code(400);

  // tell the user
  echo json_encode(
    array(
      "error" => "Need to provide parameter `lieferant_id`."
    )
  );

  die();
}

if (is_null($artikel_nr)) {
  // artikel_nr obligatory, so die() (exit) if not present

  // set response code - 400 bad request
  http_response_code(400);

  // tell the user
  echo json_encode(
    array(
      "error" => "Need to provide parameter `artikel_nr`."
    )
  );

  die();
}

$artikel_data = isset($_POST['data']) ? $_POST['data'] : null;
print($artikel_data);
$ret = $artikel->create_by_lief_id($lieferant_id, $artikel_nr, $artikel_data);

http_response_code($ret["status"]);

if (!$ret["success"]) {
  // there was a DB error
  // tell the user
  echo json_encode(
    array(
      "error" => $ret["error"]
    )
  );
} else {
  echo json_encode(array(
    "message" => "Success",
    "lieferant_id" => $lieferant_id,
    "artikel_nr" => $artikel_nr
  ));
}
?>