<?php

/***************************/
/* Read all produktgruppen */
/***************************/

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
$aktiv = isset($_GET['aktiv']) ? $_GET['aktiv'] : true;

$produktgruppen_data = NULL;
$produktgruppen_data = $produktgruppe->read_all($aktiv);

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