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
      return $row['ex'] == '1' ? TRUE : FALSE;
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
      return $row['ex'] == '1' ? TRUE : FALSE;
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
        "success" => FALSE,
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

    try {
      // execute query
      if ($stmt->execute()) {
        return [
          "success" => TRUE,
          // OK
          "status" => 200,
          "error" => ""
        ];
      } else {
        return [
          "success" => FALSE,
          // Internal server error
          "status" => 500,
          "error" => "Unable to create record"
        ];
      }
    } catch (PDOException $e) {
      return [
        "success" => FALSE,
        // Internal server error
        "status" => 500,
        "error" => $e->getMessage()
      ];
    }
  }

  // function create_by_lief_some_name($lieferant_name, $artikel_nr, $which_name)
  // {
  //   if ($this->exists_by_lief_some_name($lieferant_name, $artikel_nr, $which_name)) {
  //     // Throw error and do not create the article, as it exists already
  //     return [
  //       "success" => FALSE,
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
  artikel_id, produktgruppen_id, produktgruppen_name AS produktgruppe, lieferant_id, lieferant_name AS lieferant,
  artikel_nr, artikel_name, kurzname, barcode, menge, einheit, vpe, setgroesse,
  vk_preis, empf_vk_preis, ek_rabatt, ek_preis, variabler_preis,
  herkunft, sortiment, lieferbar, beliebtheit, bestand, von, bis, artikel.aktiv
  FROM artikel
  INNER JOIN produktgruppe USING (produktgruppen_id)
  INNER JOIN lieferant USING (lieferant_id)";

  public function read_all($count, $page, $aktiv = TRUE, $order_by = "artikel_id", $order_asc = TRUE)
  {
    $orders = array(
      "artikel_id",
      "produktgruppe",
      "lieferant",
      "artikel_nr",
      "artikel_name",
      "kurzname",
      "barcode",
      "menge",
      "einheit",
      "vpe",
      "setgroesse",
      "vk_preis",
      "empf_vk_preis",
      "ek_rabatt",
      "ek_preis",
      "variabler_preis",
      "herkunft",
      "sortiment",
      "lieferbar",
      "beliebtheit",
      "bestand",
      "von",
      "bis",
      "artikel.aktiv"
    );
    $key = array_search($order_by, $orders);
    if ($key === FALSE) { // column not found
      return [
        "success" => FALSE,
        // bad request
        "status" => 400,
        "error" => "Unknown `order_by` column '$order_by'."
      ];
    }
    $order = $orders[$key];
    $query = $this->read_query . ($aktiv ? " WHERE artikel.aktiv " : " ") .
      "ORDER BY $order " . ($order_asc ? "ASC" : "DESC") . " LIMIT ? OFFSET ?";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    // instead of PDO::PARAM_INT explicitly, could also try `$db->setAttribute(PDO::ATTR_EMULATE_PREPARES, FALSE);` globally
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
      return [
        "success" => TRUE,
        // OK
        "status" => 200,
        "error" => "",
        "data" => $arr
      ];
    }

    return [
      "success" => FALSE,
      // service unavailable
      "status" => 503,
      "error" => "Unable to access DB."
    ];
  }

  public function read_by_lief_id($lieferant_id, $artikel_nr, $aktiv = TRUE)
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

  function read_by_lief_some_name($lieferant_name, $artikel_nr, $which_name, $aktiv = TRUE)
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

  public function read_by_lief_name($lieferant_name, $artikel_nr, $aktiv = TRUE)
  {
    $res = $this->read_by_lief_some_name($lieferant_name, $artikel_nr, "lieferant_name", $aktiv);
    return $res;
  }

  public function read_by_lief_kurzname($lieferant_kurzname, $artikel_nr, $aktiv = TRUE)
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

  public function deactivate_by_artikel_id($artikel_id)
  {
    $query = "UPDATE artikel
      SET aktiv = FALSE, bis = NOW()
      WHERE artikel_id = ?";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $artikel_id);

    try {
      // execute query
      if (!$stmt->execute()) {
        return [
          "success" => FALSE,
          // Internal server error
          "status" => 500,
          "error" => "Unable to deactivate old article."
        ];
      }
    } catch (PDOException $e) {
      return [
        "success" => FALSE,
        // Internal server error
        "status" => 500,
        "error" => $e->getMessage()
      ];
    }

    return [
      "success" => TRUE,
      // OK
      "status" => 200,
      "error" => ""
    ];
  }

  public function update_by_lief_id($lieferant_id, $artikel_nr, $data)
  {
    if (!$this->exists_by_lief_id($lieferant_id, $artikel_nr)) {
      // Throw error and do not create the article, as it exists already
      return [
        "success" => FALSE,
        // bad request
        "status" => 400,
        "error" => "Article with (lieferant_id, artikel_nr) = (" . $lieferant_id . ", " . $artikel_nr . ") does not exist."
      ];
    }
    $old_data = $this->read_by_lief_id($lieferant_id, $artikel_nr);
    $this->update($old_data, $data);
  }

  public function update($old_data, $data)
  {
    // Step 1: Set old article inactive
    $res = $this->deactivate_by_artikel_id($old_data["artikel_id"]);

    if (!$res["success"]) {
      return $res;
    }

    // Step 2: Find produktgruppen_id and lieferant_id
    // (only if not directly provided in $data)
    if (!array_key_exists("lieferant_id", $data)) {
      if (array_key_exists("lieferant_name", $data)) {
        // new lieferant was specified, find lieferant_id
        $res = $this->read_by_lief_name($data["lieferant_name"]);
        if (!$res["success"]) {
          return $res;
        }
        $data["lieferant_id"] = $res["data"]["lieferant_id"];
      }
      $data["lieferant_id"] = $old_data["lieferant_id"];
    }
    if (!array_key_exists("artikel_nr", $data)) {
      $data["artikel_nr"] = $old_data["artikel_nr"];
    }

    // Step 3: Create new article
    // (replace original data in $old_data with new data in $data,
    //  adopt values not provided in $data from $old_data)
    $query = "INSERT INTO artikel
        SET lieferant_id = :lieferant_id,
            artikel_nr = :artikel_nr,
            aktiv = TRUE,
            von = NOW(),
            bis = NULL";

    // prepare query statement
    $stmt = $this->conn->prepare($query);

    // bind parameters
    $stmt->bindParam(":lieferant_id", $old_data["lieferant_id"]);
    $stmt->bindParam(":artikel_nr", $old_data["artikel_nr"]);

    try {
      // execute query
      if ($stmt->execute()) {
        return [
          "success" => TRUE,
          // OK
          "status" => 200,
          "error" => ""
        ];
      } else {
        return [
          "success" => FALSE,
          // Internal server error
          "status" => 500,
          "error" => "Unable to create new article"
        ];
      }
    } catch (PDOException $e) {
      return [
        "success" => FALSE,
        // Internal server error
        "status" => 500,
        "error" => $e->getMessage()
      ];
    }
  }

  /**************
   * DELETE     *
   **************/

  public function delete_by_lief_id($lieferant_id, $artikel_nr)
  {
    if (!$this->exists_by_lief_id($lieferant_id, $artikel_nr)) {
      // Throw error and do not create the article, as it exists already
      return [
        "success" => FALSE,
        "status" => 400,
        // bad request
        "error" => "Article with (lieferant_id, artikel_nr) = (" . $lieferant_id . ", " . $artikel_nr . ") does not exist."
      ];
    }
    $query = "UPDATE artikel
      SET aktiv = FALSE, bis = NOW()
      WHERE lieferant_id = ? AND artikel_nr = ?";

    // prepare query statement
    $stmt = $this->conn->prepare($query);
    $stmt->bindParam(1, $lieferant_id);
    $stmt->bindParam(2, $artikel_nr);

    try {
      // execute query
      if ($stmt->execute()) {
        return [
          "success" => TRUE,
          // OK
          "status" => 200,
          "error" => ""
        ];
      } else {
        return [
          "success" => FALSE,
          // Internal server error
          "status" => 500,
          "error" => "Unable to create record"
        ];
      }
    } catch (PDOException $e) {
      return [
        "success" => FALSE,
        // Internal server error
        "status" => 500,
        "error" => $e->getMessage()
      ];
    }
  }
}
?>