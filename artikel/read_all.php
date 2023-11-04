<?php

/*********************/
/* Read all articles */
/*********************/
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
$count = isset($_GET['count']) ? $_GET['count'] : 10;
$page = isset($_GET['page']) ? $_GET['page'] : 1; // first page: 1
$aktiv = isset($_GET['aktiv']) ? $_GET['aktiv'] : true;

$artikel_data = NULL;
$artikel_data = $artikel->read_all($count, $page, $aktiv);

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