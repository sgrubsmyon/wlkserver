<?php
class Artikel
{
  // database connection and table name
  private $conn;

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
  public function __construct($db)
  {
    $this->conn = $db;
  }

  /**************
   * EXISTS     *
   **************/

  // check if a product already exists in the DB
  public function exists_by_lief_id($lieferant_id, $artikel_nr)
  {
    $query = "SELECT COUNT(*) > 0 AS ex FROM artikel
    WHERE lieferant_id = ? AND LOWER(artikel_nr) = LOWER(?) AND artikel.aktiv";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_id);
    $stmt->bindParam(2, $artikel_nr);

    // execute query
    if ($stmt->execute()) {
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row['ex'] == '1' ? true : false;
    }

    return NULL;
  }

  function exists_by_lief_some_name($lieferant_name, $artikel_nr, $which_name)
  {
    $query = "SELECT COUNT(*) > 0 AS ex FROM artikel
    INNER JOIN lieferant USING (lieferant_id)
    WHERE LOWER(" . $which_name . ") = LOWER(?)
    AND LOWER(artikel_nr) = LOWER(?) AND artikel.aktiv";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_name);
    $stmt->bindParam(2, $artikel_nr);

    // execute query
    if ($stmt->execute()) {
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row['ex'] == '1' ? true : false;
    }

    return NULL;
  }

  public function exists_by_lief_name($lieferant_name, $artikel_nr)
  {
    $res = $this->exists_by_lief_some_name($lieferant_name, $artikel_nr, "lieferant_name");
    return $res;
  }

  public function exists_by_lief_kurzname($lieferant_kurzname, $artikel_nr)
  {
    $res = $this->exists_by_lief_some_name($lieferant_kurzname, $artikel_nr, "lieferant_kurzname");
    return $res;
  }

  /**************
   * CREATE     *
   **************/

  public function create_by_lief_id($lieferant_id, $artikel_nr, $data)
  {
    if ($this->exists_by_lief_id($lieferant_id, $artikel_nr)) {
      // Throw error and do not create the article, as it exists already
      return [
        "success" => false,
        "status" => 400,
        // bad request
        "error" => "Article with (lieferant_id, artikel_nr) = (" . $lieferant_id . ", " . $artikel_nr . ") already exists."
      ];
    }
    $query = "INSERT INTO artikel SET 
      lieferant_id = ?, artikel_nr = ?";
    foreach ($data as $field => $value) {
      $query .= ", " . $field . " = ?";
    }
    $query .= ", von = NOW()";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_id);
    $stmt->bindParam(2, $artikel_nr);
    $i = 3;
    foreach ($data as $field => $value) {
      $stmt->bindParam($i, $value);
      $i++;
    }

    // execute query
    if ($stmt->execute()) {
      return [
        "success" => true,
        // OK
        "status" => 200,
        "error" => ""
      ];
    } else {
      return [
        "success" => false,
        // Internal server error
        "status" => 500,
        "error" => "Unable to create record"
      ];
    }
  }

  // function create_by_lief_some_name($lieferant_name, $artikel_nr, $which_name)
  // {
  //   if ($this->exists_by_lief_some_name($lieferant_name, $artikel_nr, $which_name)) {
  //     // Throw error and do not create the article, as it exists already
  //     return [
  //       "success" => false,
  //       "status" => 400,
  //       // bad request
  //       "error" => "Article with (" . $which_name . ", artikel_nr) = (" . $lieferant_name . ", " . $artikel_nr . ") already exists."
  //     ];
  //   }
  //   $query = "INSERT INTO artikel
  //   INNER JOIN lieferant USING (lieferant_id)
  //   SET 
  //     lieferant_id = ?, artikel_nr = ?";
  //   foreach ($data as $field => $value) {
  //     $query .= ", " . $field . " = ?";
  //   }
  //   $query .= ", von = NOW()";
  // }

  /**************
   * READ       *
   **************/

  private $read_query = "SELECT
  artikel_id, produktgruppen_name AS produktgruppe, lieferant_name AS lieferant,
  artikel_nr, artikel_name, kurzname, barcode, menge, einheit, vpe, setgroesse,
  vk_preis, empf_vk_preis, ek_rabatt, ek_preis, variabler_preis,
  herkunft, sortiment, lieferbar, beliebtheit, bestand, von, bis, artikel.aktiv
  FROM artikel
  INNER JOIN produktgruppe USING (produktgruppen_id)
  INNER JOIN lieferant USING (lieferant_id)";

  public function read_all($count, $page, $aktiv = true)
  {
    $query = $this->read_query . ($aktiv ? " WHERE artikel.aktiv " : " ") .
      "LIMIT ? OFFSET ?";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $count, PDO::PARAM_INT);
    $offset = ($page - 1) * $count;
    $stmt->bindParam(2, $offset, PDO::PARAM_INT);

    // execute query
    if ($stmt->execute()) {
      $arr = array();
      $num = $stmt->rowCount();
      if ($num > 0) {
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
          array_push($arr, $row);
        }
      }
      return $arr;
    }

    return NULL;
  }

  public function read_by_lief_id($lieferant_id, $artikel_nr, $aktiv = true)
  {
    $query = $this->read_query . " WHERE lieferant_id = ? AND LOWER(artikel_nr) = LOWER(?) " .
      ($aktiv ? "AND artikel.aktiv " : "") . "ORDER BY artikel_id DESC";
    // return array("message" => $query);

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_id);
    $stmt->bindParam(2, $artikel_nr);

    // execute query
    if ($stmt->execute()) {
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row;
    }

    return NULL;
  }

  function read_by_lief_some_name($lieferant_name, $artikel_nr, $which_name, $aktiv = true)
  {
    $query = $this->read_query . " WHERE LOWER(" . $which_name . ") = LOWER(?) AND LOWER(artikel_nr) = LOWER(?) " .
      ($aktiv ? "AND artikel.aktiv " : "") . "ORDER BY artikel_id DESC";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_name);
    $stmt->bindParam(2, $artikel_nr);

    // execute query
    if ($stmt->execute()) {
      // retrieve our table contents
      // fetch() is faster than fetchAll()
      // http://stackoverflow.com/questions/2770630/pdofetchall-vs-pdofetch-in-a-loop
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      return $row;
    }

    return NULL;
  }

  public function read_by_lief_name($lieferant_name, $artikel_nr, $aktiv = true)
  {
    $res = $this->read_by_lief_some_name($lieferant_name, $artikel_nr, "lieferant_name", $aktiv);
    return $res;
  }

  public function read_by_lief_kurzname($lieferant_kurzname, $artikel_nr, $aktiv = true)
  {
    $res = $this->read_by_lief_some_name($lieferant_kurzname, $artikel_nr, "lieferant_kurzname", $aktiv);
    return $res;
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
  //   return NULL;
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
  //   return NULL;
  // }

  /**************
   * UPDATE     *
   **************/

  /**************
   * DELETE     *
   **************/
}
?>