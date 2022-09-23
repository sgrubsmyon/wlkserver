<?php
class Produktgruppe {
  // database connection and table name
  private $conn;
  private $table_name = "artikel";

  // constructor with $db as database connection
  public function __construct($db) {
    $this->conn = $db;
  }

  // read all produktgruppen
  function read_all($typ) {
    // select all query
    $query = "SELECT DISTINCT
        produktgruppen_name
      FROM " . $this->table_name . "
      WHERE typ = ?
      ORDER BY produktgruppen_name";
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $typ);
    if ($stmt->execute()) {
      $produktgruppen_arr = array();
      $num = $stmt->rowCount();
      if ($num > 0) {
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
          array_push($produktgruppen_arr, $row["produktgruppen_name"]);
        }
      }
      return $produktgruppen_arr;
    }
    return NULL;
  }
}
?>
