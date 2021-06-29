#!/bin/sh

if test -w /usr/include/openssl/e_os2.h; then
    (set -x

    # behave as if the code was preprocessed with -DDEBUG_UNUSED
    sed -i /usr/include/openssl/e_os2.h \
        -e 's|\(# *if\)def DEBUG_UNUSED|\1 1|')
fi

if test -w /usr/include/openssl/evp.h && rpm -q openssl-devel | grep openssl-devel-3.0; then
    # apply patch of <openssl/evp.h> from https://github.com/openssl/openssl/pull/15905
    patch --force --no-backup-if-mismatch --reject-file=- /usr/include/openssl/evp.h << EOF
--- a/include/openssl/evp.h
+++ b/include/openssl/evp.h
@@ -638,7 +638,7 @@ void BIO_set_md(BIO *, const EVP_MD *md);
 # define BIO_get_cipher_status(b)   BIO_ctrl(b,BIO_C_GET_CIPHER_STATUS,0,NULL)
 # define BIO_get_cipher_ctx(b,c_pp) BIO_ctrl(b,BIO_C_GET_CIPHER_CTX,0,(c_pp))
 
-/*__owur*/ int EVP_Cipher(EVP_CIPHER_CTX *c,
+__owur int EVP_Cipher(EVP_CIPHER_CTX *c,
                           unsigned char *out,
                           const unsigned char *in, unsigned int inl);
 
@@ -712,7 +712,7 @@ int EVP_CIPHER_CTX_test_flags(const EVP_CIPHER_CTX *ctx, int flags);
 
 __owur int EVP_EncryptInit(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                            const unsigned char *key, const unsigned char *iv);
-/*__owur*/ int EVP_EncryptInit_ex(EVP_CIPHER_CTX *ctx,
+__owur int EVP_EncryptInit_ex(EVP_CIPHER_CTX *ctx,
                                   const EVP_CIPHER *cipher, ENGINE *impl,
                                   const unsigned char *key,
                                   const unsigned char *iv);
@@ -720,16 +720,16 @@ __owur int EVP_EncryptInit_ex2(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                                const unsigned char *key,
                                const unsigned char *iv,
                                const OSSL_PARAM params[]);
-/*__owur*/ int EVP_EncryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
+__owur int EVP_EncryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
                                  int *outl, const unsigned char *in, int inl);
-/*__owur*/ int EVP_EncryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *out,
+__owur int EVP_EncryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *out,
                                    int *outl);
-/*__owur*/ int EVP_EncryptFinal(EVP_CIPHER_CTX *ctx, unsigned char *out,
+__owur int EVP_EncryptFinal(EVP_CIPHER_CTX *ctx, unsigned char *out,
                                 int *outl);
 
 __owur int EVP_DecryptInit(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                            const unsigned char *key, const unsigned char *iv);
-/*__owur*/ int EVP_DecryptInit_ex(EVP_CIPHER_CTX *ctx,
+__owur int EVP_DecryptInit_ex(EVP_CIPHER_CTX *ctx,
                                   const EVP_CIPHER *cipher, ENGINE *impl,
                                   const unsigned char *key,
                                   const unsigned char *iv);
@@ -737,17 +737,17 @@ __owur int EVP_DecryptInit_ex2(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                                const unsigned char *key,
                                const unsigned char *iv,
                                const OSSL_PARAM params[]);
-/*__owur*/ int EVP_DecryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
+__owur int EVP_DecryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
                                  int *outl, const unsigned char *in, int inl);
 __owur int EVP_DecryptFinal(EVP_CIPHER_CTX *ctx, unsigned char *outm,
                             int *outl);
-/*__owur*/ int EVP_DecryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *outm,
+__owur int EVP_DecryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *outm,
                                    int *outl);
 
 __owur int EVP_CipherInit(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                           const unsigned char *key, const unsigned char *iv,
                           int enc);
-/*__owur*/ int EVP_CipherInit_ex(EVP_CIPHER_CTX *ctx,
+__owur int EVP_CipherInit_ex(EVP_CIPHER_CTX *ctx,
                                  const EVP_CIPHER *cipher, ENGINE *impl,
                                  const unsigned char *key,
                                  const unsigned char *iv, int enc);
@@ -781,18 +781,18 @@ __owur int EVP_DigestVerify(EVP_MD_CTX *ctx, const unsigned char *sigret,
                             size_t siglen, const unsigned char *tbs,
                             size_t tbslen);
 
-int EVP_DigestSignInit_ex(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
+__owur int EVP_DigestSignInit_ex(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
                           const char *mdname, OSSL_LIB_CTX *libctx,
                           const char *props, EVP_PKEY *pkey,
                           OSSL_PARAM params[]);
-/*__owur*/ int EVP_DigestSignInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
+__owur int EVP_DigestSignInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
                                   const EVP_MD *type, ENGINE *e,
                                   EVP_PKEY *pkey);
-int EVP_DigestSignUpdate(EVP_MD_CTX *ctx, const void *data, size_t dsize);
+__owur int EVP_DigestSignUpdate(EVP_MD_CTX *ctx, const void *data, size_t dsize);
 __owur int EVP_DigestSignFinal(EVP_MD_CTX *ctx, unsigned char *sigret,
                                size_t *siglen);
 
-int EVP_DigestVerifyInit_ex(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
+__owur int EVP_DigestVerifyInit_ex(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx,
                             const char *mdname, OSSL_LIB_CTX *libctx,
                             const char *props, EVP_PKEY *pkey,
                             OSSL_PARAM params[]);
EOF
fi
