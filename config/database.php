<?php
class Database {
    // specify your own database credentials
    private $host = "localhost";
    private $db_name = "kasse";
    private $username = "mitarbeiter";
    private $password = "p";
    public $conn;

    // get the database connection
    public function getConnection(){
        $this->conn = NULL;
        try {
            $this->conn = new PDO("mysql:host=" . $this->host . ";dbname=" . $this->db_name, $this->username, $this->password);
            $this->conn->exec("SET NAMES utf8");
        } catch (PDOException $exception){
            echo "Connection error: " . $exception->getMessage();
        }
        return $this->conn;
    }
}
?>
