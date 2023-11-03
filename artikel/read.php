<?php

/***********************/
/* Read single article */
/***********************/
/* Set aktiv=true to select only the currently active ones */
/* Set aktiv=false to show also the history of inactive ones */

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
$lieferant_id = isset($_GET['li']) ? $_GET['li'] : NULL;
$lieferant_name = isset($_GET['ln']) ? $_GET['ln'] : NULL;
$lieferant_kurzname = isset($_GET['lkn']) ? $_GET['lkn'] : NULL;
$artikel_nr = isset($_GET['an']) ? $_GET['an'] : NULL;
$aktiv = isset($_GET['aktiv']) ? $_GET['aktiv'] : true;

if (is_null($artikel_nr)) {
  // artikel_nr obligatory, so die() (exit) if not present

  // set response code - 400 bad request
  http_response_code(400);

  // tell the user
  echo json_encode(
    array(
      "error" => "Need to provide `artikel_nr` with URL parameter `an`."
    )
  );

  die();
}

if (is_null($lieferant_id) && is_null($lieferant_name) && is_null($lieferant_kurzname)) {
  // set response code - 400 bad request
  http_response_code(400);

  // tell the user
  echo json_encode(
    array(
      "error" => "Need to provide either `lieferant_id` with URL parameter `li` " .
        "or `lieferant_name` with URL parameter `ln` " .
        "or `lieferant_kurzname` with URL parameter `lkn`."
    )
  );

  die();
}

$artikel_data = NULL;
if (!is_null($lieferant_id)) {
  $artikel_data = $artikel->read_by_lief_id($lieferant_id, $artikel_nr, $aktiv);
} else if (!is_null($lieferant_name)) {
  $artikel_data = $artikel->read_by_lief_name($lieferant_name, $artikel_nr, $aktiv);
} else if (!is_null($lieferant_kurzname)) {
  $artikel_data = $artikel->read_by_lief_kurzname($lieferant_kurzname, $artikel_nr, $aktiv);
}

if (is_null($artikel_data)) {
  // there was a DB error

  // set response code - 503 service unavailable
  http_response_code(503);

  // tell the user
  echo json_encode(
    array(
      "error" => "Unable to access DB."
    )
  );
} else {
  // set response code - 200 OK
  http_response_code(200);

  // show product data in json format
  // echo json_encode(array(
  //   "result" => $exists
  // ));
  echo json_encode($artikel_data);
}
?>