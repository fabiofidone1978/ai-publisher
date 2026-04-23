<?php
/**
 * get_newsletter_emails.php
 * Restituisce la lista email dalla tabella newsletter in formato JSON.
 * Da caricare su www.fabiofidone.it/
 */

define('TOKEN', 'fabiofidone_secure_token_2026');

header('Content-Type: application/json; charset=utf-8');

if (($_GET['token'] ?? '') !== TOKEN) {
    http_response_code(403);
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

$host = '31.11.39.211';
$db   = 'Sql1855273_2';
$user = 'Sql1855273';
$pass = 'Daniela.77';

try {
    $pdo = new PDO(
        "mysql:host=$host;dbname=$db;charset=utf8mb4",
        $user,
        $pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 5]
    );

    $stmt = $pdo->query("SELECT email FROM newsletter WHERE email IS NOT NULL AND email != '' ORDER BY id ASC");
    $emails = $stmt->fetchAll(PDO::FETCH_COLUMN);

    echo json_encode(['status' => 'ok', 'count' => count($emails), 'emails' => $emails]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
