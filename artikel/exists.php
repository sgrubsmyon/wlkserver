<?php
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

// read parameters from GET method
$lieferant_id = isset($_GET['li']) ? (int)$_GET['li'] : NULL;
$lieferant_name = isset($_GET['ln']) ? $_GET['ln'] : NULL;
$lieferant_kurzname = isset($_GET['lkn']) ? $_GET['lkn'] : NULL;
$artikel_nr = isset($_GET['an']) ? $_GET['an'] : NULL;

if (is_null($artikel_nr)) {
  // artikel_nr obligatory, so die() (exit) if not present
  
  // set response code - 400 bad request
  http_response_code(400);

  // tell the user
  echo json_encode(array(
    "error" => "Need to provide `artikel_nr` with URL parameter `an`."
  ));

  die();
}

if (is_null($lieferant_id) && is_null($lieferant_name) && is_null($lieferant_kurzname)) {
  // set response code - 400 bad request
  http_response_code(400);
  
  // tell the user
  echo json_encode(array(
    "error" => "Need to provide either `lieferant_id` with URL parameter `li` ".
    "or `lieferant_name` with URL parameter `ln` ".
    "or `lieferant_kurzname` with URL parameter `lkn`."
  ));
  
  die();
}

$exists = NULL;
if (!is_null($lieferant_id)) {
  $exists = $artikel->exists_by_lief_id($lieferant_id, $artikel_nr);
} else if (!is_null($lieferant_name)) {
  $exists = $artikel->exists_by_lief_name($lieferant_name, $artikel_nr);
} else if (!is_null($lieferant_kurzname)) {
  $exists = $artikel->exists_by_lief_kurzname($lieferant_kurzname, $artikel_nr);
}

if (is_null($exists)) {
  // there was a DB error

  // set response code - 503 service unavailable
  http_response_code(503);

  // tell the user
  echo json_encode(array(
    "error" => "Unable to access DB."
  ));
} else {
  // set response code - 200 OK
  http_response_code(200);

  // show product data in json format
  echo json_encode(array(
    "result" => $exists
  ));
}
?>
