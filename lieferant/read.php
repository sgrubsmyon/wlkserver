<?php

/*************************/
/* Read single lieferant */
/*************************/
/* Set aktiv=true to select only the currently active ones */
/* Set aktiv=false to show also the history of inactive ones */

// required headers
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

// include database and object files
include_once '../config/database.php';
include_once '../objects/lieferant.php';

// instantiate database and lieferant object
$database = new Database();
$db = $database->getConnection();

// initialize object
$lieferant = new Lieferant($db);

// read parameters from GET method
$lieferant_id = isset($_GET['li']) ? (int)$_GET['li'] : NULL;
$lieferant_name = isset($_GET['ln']) ? $_GET['ln'] : NULL;
$lieferant_kurzname = isset($_GET['lkn']) ? $_GET['lkn'] : NULL;
$aktiv = isset($_GET['aktiv']) ? filter_var($_GET['aktiv'], FILTER_VALIDATE_BOOLEAN) : TRUE;

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

$lieferant_data = NULL;
if (!is_null($lieferant_id)) {
  $lieferant_data = $lieferant->read_by_lief_id($lieferant_id, $aktiv);
} else if (!is_null($lieferant_name)) {
  $lieferant_data = $lieferant->read_by_lief_name($lieferant_name, $aktiv);
} else if (!is_null($lieferant_kurzname)) {
  $lieferant_data = $lieferant->read_by_lief_kurzname($lieferant_kurzname, $aktiv);
}

if (is_null($lieferant_data)) {
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
  echo json_encode($lieferant_data);
}
?>