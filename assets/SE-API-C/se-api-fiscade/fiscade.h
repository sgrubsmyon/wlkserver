#include <se_api.h>
#include <se_memory_util.h>


#include <se_types_ex.h>
#include <se_transport_ex.h>


#define worm_uint uint64_t

typedef enum WormUserId {
	WORM_USER_ADMIN = 1,
	WORM_USER_TIME_ADMIN = 2
} WormUserId;
// https://support.gastro-mis.de/support/solutions/articles/36000170390-erste-schritte-bei-der-anbindung
typedef enum WormInitializationState {
	Uninitialized = 0,
	Initialized = 1,
	Decommissioned = 2,
	InitStateUnknown = -1 // added by cv
} WormInitializationState;
typedef struct WormRegisteredClients {
	/** Amount of client ids stored in clientIds. */
	int amount;
	/** List of NULL terminated client ids. */
	char clientIds[16][31];
} WormRegisteredClients;
// https://support.gastro-mis.de/support/solutions/articles/36000180682-code-samples
typedef int WormExportTarCallback (const unsigned char *chunk, unsigned int chunkLength, void *callbackData);
typedef int WormExportTarIncrementalCallback (const unsigned char* chunk, unsigned int chunkLength, uint32_t processedBlocks, uint32_t totalBlocks, void* callbackData);

typedef enum Worm_EntryType {
	/* A transaction. */
	WORM_ENTRY_TYPE_TRANSACTION = 0,

	/* A system log message. */
	WORM_ENTRY_TYPE_SYSTEM_LOG_MESSAGE = 1,

	/* A SE Audit log message. */
	WORM_ENTRY_TYPE_SE_AUDIT_LOG_MESSAGE = 2
} WormEntryType;

#if defined(FISCADE)
#	if defined(_WIN32)
#		define	FIS_EXPORT __declspec(dllexport)
#	else
#		define	FIS_EXPORT __attribute__ ((visibility ("default")))
#	endif
#else
#	define FIS_EXPORT
#endif


typedef struct WormTransactionResponse {
	worm_uint logTime;
	unsigned char* serialNumber;
	worm_uint serialNumberLength;
	worm_uint signatureCounter;
	unsigned char* signature;
	worm_uint signatureLength;
	worm_uint transactionNumber;
} WormTransactionResponse;

typedef struct WormContext {
	se_ctx_t* se;
	WormTransactionResponse* lastTransactionResponse;
	char lastClientId[32];
} WormContext;

typedef struct WormEntry {
	WormContext* context;
	int isValid;
	uint32_t id;
	WormEntryType type;
	unsigned char* logMessage;
	worm_uint msgLength;
	worm_uint processDataLength;
	unsigned char* processData;
} WormEntry;

#define WORMAPI FIS_EXPORT
#define WORMAPI_CALL

// there is no limit implemented for cryptovision TSE, but 10 Mio is the product spec
#define MAX_SIGNATURES 10000000

typedef struct WormInfo {
	WormContext* context;
	se_pin_state_flags_t pin_state;
	se_lcs_t lcs;
	uint32_t timeSyncInterval;
	uint32_t signatureCounter;
	const char* customizationIdentifier;
	uint8_t isEngineeringSample;
	uint64_t sizeOfMemory;
	uint64_t freeMemory;
	uint32_t maxNumberTransactions;
	uint32_t currentNumberTransactions;
	unsigned char* publicKey;
	uint32_t publicKeyLength;
	unsigned char* serialNumber;
	uint32_t serialNumberLength;
	char* description;
	uint32_t descriptionLength;
	uint32_t numberOfClients;
	uint32_t maxNumberOfClients;
	int64_t expirationDate;
	uint64_t exportSize;
	const char* formFactor;
} WormInfo;

#include <fiscade_wormError.h>
typedef enum WormError WormError;

#include <fiscade_wormApi.h>
