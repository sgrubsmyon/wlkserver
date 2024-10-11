<?php
class Lieferant
{
  // database connection and table name
  private $conn;

  // constructor with $db as database connection
  public function __construct($db)
  {
    $this->conn = $db;
  }

  /**************
   * EXISTS     *
   **************/

  /**************
   * CREATE     *
   **************/

  /**************
   * READ *
   **************/

  private $read_query = "SELECT
artikel_id, produktgruppen_id, produktgruppen_name AS produktgruppe, lieferant_id, lieferant_name AS lieferant,
artikel_nr, artikel_name, kurzname, barcode, menge, einheit, vpe, setgroesse,
vk_preis, empf_vk_preis, ek_rabatt, ek_preis, variabler_preis,
herkunft, sortiment, lieferbar, beliebtheit, bestand, von, bis, artikel.aktiv
FROM artikel
INNER JOIN produktgruppe USING (produktgruppen_id)
INNER JOIN lieferant USING (lieferant_id)";

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

  /**************
   * UPDATE     *
   **************/

  /**************
   * DELETE     *
   **************/

}
?>