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
$count = isset($_GET['count']) ? (int)$_GET['count'] : 10;
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1; // first page: 1
$aktiv = isset($_GET['aktiv']) ? filter_var($_GET['aktiv'], FILTER_VALIDATE_BOOLEAN) : TRUE;
$order_by = isset($_GET['order_by']) ? $_GET['order_by'] : "artikel_id";
$order_asc = isset($_GET['order_asc']) ? filter_var($_GET['order_asc'], FILTER_VALIDATE_BOOLEAN) : TRUE;

$ret = $artikel->read_all($count, $page, $aktiv, $order_by, $order_asc);

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
  echo json_encode($ret["data"]);
}
?>