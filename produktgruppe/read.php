<?php

/*****************************/
/* Read single product group */
/*****************************/
/* Set aktiv=true to select only the currently active ones */
/* Set aktiv=false to show also the history of inactive ones */

// required headers
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");

// include database and object files
include_once '../config/database.php';
include_once '../objects/produktgruppe.php';

// instantiate database and artikel object
$database = new Database();
$db = $database->getConnection();

// initialize object
$produktgruppe = new Produktgruppe($db);

// read parameters from GET method
$produktgruppen_id = isset($_GET['id']) ? (int)$_GET['id'] : NULL;
$aktiv = isset($_GET['aktiv']) ? filter_var($_GET['aktiv'], FILTER_VALIDATE_BOOLEAN) : TRUE;

if (is_null($produktgruppen_id)) {
    // produktgruppen_id obligatory, so die() (exit) if not present

    // set response code - 400 bad request
    http_response_code(400);

    // tell the user
    echo json_encode(
        array(
            "error" => "Need to provide `produktgruppen_id` with URL parameter `id`."
        )
    );

    die();
}

$produktgruppen_data = NULL;
$produktgruppen_data = $produktgruppe->read_single_by_id($produktgruppen_id, $aktiv);

if (is_null($produktgruppen_data)) {
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
    echo json_encode($produktgruppen_data);
}
?>