<?php
class Produktgruppe
{
  // database connection and table name
  private $conn;

  // constructor with $db as database connection
  public function __construct($db)
  {
    $this->conn = $db;
  }

  // read all produktgruppen, choose with $aktiv whether
  //   only the active ones or also the inactive ones
  public function read_all($aktiv = true)
  {
    // select all query
    $query = "SELECT * FROM produktgruppe" . ($aktiv ? " WHERE aktiv" : "") . "
      ORDER BY produktgruppen_id";

    $stmt = $this->conn->prepare($query);
    if ($stmt->execute()) {
      $produktgruppen_arr = array();
      $num = $stmt->rowCount();
      if ($num > 0) {
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
          array_push($produktgruppen_arr, $row);
        }
      }
      return $produktgruppen_arr;
    }

    return NULL;
  }

  // read single produktgruppe, choose with $aktiv whether
  //   only the active ones or also the inactive ones
  public function read_single_by_id($produktgruppen_id, $aktiv = true)
  {
    $query = "SELECT * FROM produktgruppe
      WHERE produktgruppen_id = ?" . ($aktiv ? " AND aktiv" : "");

    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $produktgruppen_id);

    // execute query
    if ($stmt->execute()) {
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row;
    }

    return NULL;
  }
}
?>