<?php

/*************************/
/* Delete single article */
/*************************/

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
// $lieferant_name = isset($_GET['ln']) ? $_GET['ln'] : NULL;
// $lieferant_kurzname = isset($_GET['lkn']) ? $_GET['lkn'] : NULL;
$artikel_nr = isset($_GET['an']) ? $_GET['an'] : NULL;

if (is_null($lieferant_id)) {
  // 400 bad request
  http_response_code(400);
  echo json_encode(
    array(
      "error" => "Need to provide parameter `lieferant_id`."
    )
  );
  die();
}

if (is_null($artikel_nr)) {
  // artikel_nr obligatory, so die() (exit) if not present
  // 400 bad request
  http_response_code(400);
  echo json_encode(
    array(
      "error" => "Need to provide parameter `artikel_nr`."
      )
  );
  die();
}

$ret = $artikel->delete_by_lief_id($lieferant_id, $artikel_nr);
http_response_code($ret["status"]);

if (!$ret["success"]) {
  echo json_encode(
    array(
      "error" => $ret["error"]
    )
  );
  die();
} else {
  echo json_encode(array(
    "message" => "Success",
    "lieferant_id" => $lieferant_id,
    "artikel_nr" => $artikel_nr
  ));
}
?>