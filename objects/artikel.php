<?php
class Artikel {
  // database connection and table name
  private $conn;
  private $table_name = "artikel";

  // these properties are useful for creating products
  // object properties
  //public $produktgruppen_name;
  //public $lieferant_name;
  //public $artikel_nr;
  //public $artikel_name;
  //public $vk_preis;
  //public $pfand;
  //public $mwst_satz;

  // constructor with $db as database connection
  public function __construct($db) {
    $this->conn = $db;
  }

  // check if a product already exists in the DB
  function exists_by_lief_id($lieferant_id, $artikel_nr) {

  }

  function exists_by_lief_name($lieferant_name, $artikel_nr) {
    $query = "SELECT COUNT(*) > 0 AS ex FROM artikel
    INNER JOIN lieferant USING (lieferant_id)
    WHERE lieferant_name = ? AND artikel_nr = ?
    AND artikel.aktiv = TRUE;";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_name);
    $stmt->bindParam(2, $artikel_nr);

     // execute query
    if ($stmt->execute()) {
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row['ex'] == '1' ? true : false;
     }

     return null;
  }

  function exists_by_lief_kurzname($lieferant_kurzname, $artikel_nr) {

  }

  // // read all products
  // function read_all() {
  //   // select all query
  //   $query = "SELECT
  //       typ, sortiment, produktgruppen_name, lieferant_name, artikel_nr, artikel_name,
  //       vk_preis, pfand, mwst_satz
  //     FROM " . $this->table_name . "
  //     ORDER BY produktgruppen_name, REPLACE(artikel_name, \"\\\"\", \"\")";

  //   // prepare query statement
  //   $stmt = $this->conn->prepare($query);

  //   // execute query
  //   if ($stmt->execute()) {
  //     // artikel array
  //     $artikel_arr = array();

  //     $num = $stmt->rowCount();
  //     if ($num > 0) {
  //       // retrieve our table contents
  //       // fetch() is faster than fetchAll()
  //       // http://stackoverflow.com/questions/2770630/pdofetchall-vs-pdofetch-in-a-loop
  //       while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
  //         array_push($artikel_arr, $row);
  //       }
  //     }
  //     return $artikel_arr;
  //   }
  //   return null;
  // }

  // // read products from one product group
  // function read_group($groupname, $typ, $sortiment_only) {
  //   // select group query
  //   $query = "SELECT
  //       typ, sortiment, produktgruppen_name, lieferant_name, artikel_nr, artikel_name,
  //       vk_preis, pfand, mwst_satz
  //     FROM " . $this->table_name . "
  //     WHERE produktgruppen_name = ? " .
  //     (is_null($typ) ? "" : "AND typ = ? ") .
  //     ($sortiment_only ? "AND sortiment = TRUE " : "") . "
  //     ORDER BY produktgruppen_name, REPLACE(artikel_name, \"\\\"\", \"\")";

  //   // prepare query statement
  //   $stmt = $this->conn->prepare($query);
  //   $stmt->bindParam(1, $groupname);
  //   if (!is_null($typ)) {
  //     $stmt->bindParam(2, $typ);
  //   }

  //   // execute query
  //   if ($stmt->execute()) {
  //     // artikel array
  //     $artikel_arr = array();

  //     $num = $stmt->rowCount();
  //     if ($num > 0) {
  //       while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
  //         array_push($artikel_arr, $row);
  //       }
  //     }
  //     return $artikel_arr;
  //   }
  //   return null;
  // }
}
?>
