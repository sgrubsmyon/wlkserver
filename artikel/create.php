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

// read URL parameters from POST method
$lieferant_id = isset($_GET['li']) ? $_GET['li'] : NULL;
$artikel_nr = isset($_GET['an']) ? $_GET['an'] : NULL;

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

// Read parameters from HTTP body of POST method
$artikel_data = json_decode(file_get_contents('php://input'), TRUE); // https://stackoverflow.com/questions/18866571/receive-json-post-with-php

if (is_null($artikel_data)) {
  // 400 bad request
  http_response_code(400);
  echo json_encode(
    array(
      "error" => "Need to provide article data as JSON inside HTTP body."
    )
  );
  die();
}

$ret = $artikel->create_by_lief_id($lieferant_id, $artikel_nr, $artikel_data);
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